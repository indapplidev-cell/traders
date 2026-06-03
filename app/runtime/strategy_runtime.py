"""Controlled runtime layer for one or more bounded strategy ticks."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.config.settings import get_settings
from app.db.models import Candle, TradeDecisionRecord
from app.db.session import session_scope
from app.execution.paper_step_service import PaperStepService
from app.execution.position_manager import PositionManager
from app.market.analysis_service import MarketAnalysisService
from app.market.candle_service import CandleService
from app.strategy.base_strategy import StrategyDecision
from app.strategy.strategy_context import StrategyContext
from app.strategy.strategy_registry import get_strategy
from app.strategy.trade_decision import DecisionType, MarketRegime, TradeDecision


@dataclass(slots=True)
class RuntimeTickResult:
    """Result of one bounded strategy tick."""

    strategy_decision: StrategyDecision
    final_action: str
    risk_approved: bool
    risk_reason: str
    execution_action: str
    execution_message: str
    decision_id: int | None
    candles_used: int
    market_regime: str | None
    portfolio_snapshot: dict[str, Any]


class StrategyRuntime:
    """Executes one or more bounded strategy ticks without live trading."""

    def __init__(
        self,
        *,
        candle_service: CandleService | None = None,
        analysis_service: MarketAnalysisService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.candle_service = candle_service or CandleService()
        self.analysis_service = analysis_service or MarketAnalysisService()

    def run_tick(
        self,
        strategy_name: str,
        symbol: str,
        interval: str,
        candle_limit: int | None = None,
    ) -> RuntimeTickResult:
        """Executes exactly one controlled strategy step."""

        normalized_symbol = symbol.upper()
        limit = candle_limit or self.settings.strategy_default_candle_limit
        strategy = get_strategy(strategy_name)

        with session_scope() as session:
            candles = self.analysis_service.load_candles(
                session=session,
                symbol=normalized_symbol,
                interval=interval,
                limit=limit,
            )

        if len(candles) < limit:
            asyncio.run(
                self.candle_service.fetch_and_store_candles(
                    symbol=normalized_symbol,
                    interval=interval,
                    limit=limit,
                )
            )
            with session_scope() as session:
                candles = self.analysis_service.load_candles(
                    session=session,
                    symbol=normalized_symbol,
                    interval=interval,
                    limit=limit,
                )

        if not candles:
            raise ValueError("No candles available for runtime tick.")

        indicator_snapshot = self.analysis_service.indicator_service.calculate(candles)
        market_regime = self.analysis_service.regime_detector.detect(indicator_snapshot)
        latest_candle = candles[-1]

        with session_scope() as session:
            manager = PositionManager(session)
            portfolio_state = manager.get_portfolio_state()
            last_decisions = self._load_last_decisions(session, normalized_symbol, interval)

            context = StrategyContext(
                symbol=normalized_symbol,
                interval=interval,
                candles=candles,
                indicators=self._build_indicators(indicator_snapshot),
                market_regime=market_regime.value,
                open_positions=portfolio_state.open_positions,
                portfolio_state=self._serialize_portfolio(portfolio_state),
                last_decisions=last_decisions,
                settings=self.settings,
            )

            strategy_decision = strategy.decide(context)
            execution_decision = self._to_trade_decision(
                strategy_decision=strategy_decision,
                market_regime=market_regime,
                latest_candle=latest_candle,
            )

            result = PaperStepService(session).process(
                execution_decision,
                indicator_snapshot=indicator_snapshot,
                latest_candle=latest_candle,
                runtime_decision=strategy_decision,
            )
            updated_portfolio = manager.get_portfolio_state()

            return RuntimeTickResult(
                strategy_decision=strategy_decision,
                final_action=result.final_decision.decision.value,
                risk_approved=result.risk_approved,
                risk_reason=result.risk_reason,
                execution_action=result.execution_action,
                execution_message=result.execution_message,
                decision_id=result.journal_id,
                candles_used=len(candles),
                market_regime=market_regime.value,
                portfolio_snapshot=self._serialize_portfolio(updated_portfolio),
            )

    def run_loop(
        self,
        strategy_name: str,
        symbol: str,
        interval: str,
        ticks: int,
        sleep_seconds: float,
    ) -> list[RuntimeTickResult]:
        """Executes a bounded strategy loop and always stops after N ticks."""

        if ticks <= 0:
            raise ValueError("ticks must be > 0")
        if ticks > self.settings.strategy_max_ticks:
            raise ValueError(
                f"ticks must be <= STRATEGY_MAX_TICKS ({self.settings.strategy_max_ticks})"
            )
        if sleep_seconds < 0:
            raise ValueError("sleep_seconds must be >= 0")

        results: list[RuntimeTickResult] = []
        for index in range(ticks):
            results.append(self.run_tick(strategy_name, symbol, interval))
            if index < ticks - 1 and sleep_seconds > 0:
                time.sleep(sleep_seconds)
        return results

    @staticmethod
    def _build_indicators(snapshot: Any) -> dict[str, Any]:
        return {
            "snapshot": snapshot,
            "ema_20": snapshot.ema_20,
            "ema_50": snapshot.ema_50,
            "ema_200": snapshot.ema_200,
            "rsi_14": snapshot.rsi_14,
            "atr_14": snapshot.atr_14,
            "volume_sma_20": snapshot.volume_sma_20,
            "last_close": snapshot.last_close,
            "last_volume": snapshot.last_volume,
        }

    @staticmethod
    def _serialize_portfolio(portfolio_state: Any) -> dict[str, Any]:
        return {
            "balance_usdt": str(portfolio_state.balance_usdt),
            "open_positions_count": len(portfolio_state.open_positions),
            "realized_pnl": str(portfolio_state.realized_pnl),
        }

    @staticmethod
    def _load_last_decisions(session: Any, symbol: str, interval: str) -> list[TradeDecisionRecord]:
        return list(
            session.execute(
                select(TradeDecisionRecord)
                .where(
                    TradeDecisionRecord.symbol == symbol,
                    TradeDecisionRecord.interval == interval,
                )
                .order_by(TradeDecisionRecord.created_at.desc(), TradeDecisionRecord.id.desc())
                .limit(5)
            )
            .scalars()
            .all()
        )

    @staticmethod
    def _to_trade_decision(
        *,
        strategy_decision: StrategyDecision,
        market_regime: MarketRegime,
        latest_candle: Candle,
    ) -> TradeDecision:
        price = Decimal(str(strategy_decision.metadata.get("price", latest_candle.close)))
        regime_name = str(strategy_decision.metadata.get("market_regime", market_regime.value)).upper()
        regime = MarketRegime(regime_name)
        created_at = latest_candle.close_time
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        else:
            created_at = created_at.astimezone(UTC)

        return TradeDecision.build(
            symbol=strategy_decision.symbol,
            interval=strategy_decision.interval,
            decision=DecisionType(strategy_decision.action),
            reason=strategy_decision.reason,
            regime=regime,
            price=price,
            created_at=created_at,
        )
