"""Persisted local backtest runner built on top of the existing BacktestEngine."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.analytics.backtest_performance import BacktestPerformanceService
from app.backtest.backtest_engine import BacktestEngine
from app.backtest.backtest_result import BacktestResult
from app.config.settings import get_settings
from app.db.models import BacktestSession, BacktestSessionMetric
from app.db.session import session_scope
from app.market.analysis_service import AnalysisResult, MarketAnalysisService
from app.strategy.strategy_registry import get_strategy

logger = logging.getLogger(__name__)


BACKTEST_STATUS_CREATED = "CREATED"
BACKTEST_STATUS_RUNNING = "RUNNING"
BACKTEST_STATUS_COMPLETED = "COMPLETED"
BACKTEST_STATUS_FAILED = "FAILED"


@dataclass(slots=True)
class BacktestRunResult:
    session_id: int
    status: str
    strategy_name: str
    symbol: str
    interval: str
    candles_used: int | None
    total_pnl: Decimal | None
    return_pct: Decimal | None
    data_quality: str
    last_error: str | None


@dataclass(slots=True)
class _RecordedDecisionStats:
    buy: int = 0
    sell: int = 0
    hold: int = 0

    def record(self, action: str) -> None:
        if action == "BUY":
            self.buy += 1
        elif action == "SELL":
            self.sell += 1
        else:
            self.hold += 1


class _RecordingAnalysisService:
    """Wrap MarketAnalysisService and capture strategy actions used in backtest."""

    def __init__(self, delegate: MarketAnalysisService) -> None:
        self._delegate = delegate
        self.stats = _RecordedDecisionStats()

    def load_candles(self, session, symbol: str, interval: str, limit: int):
        return self._delegate.load_candles(session=session, symbol=symbol, interval=interval, limit=limit)

    def analyze(self, *, symbol: str, interval: str, candles) -> AnalysisResult:
        result = self._delegate.analyze(symbol=symbol, interval=interval, candles=candles)
        self.stats.record(result.strategy_decision.decision.value)
        return result


class BacktestRunner:
    """Create persisted backtest sessions without rewriting BacktestEngine."""

    def __init__(self, *, engine: BacktestEngine | None = None) -> None:
        self.settings = get_settings()
        self._engine = engine

    def run(
        self,
        strategy_name: str,
        symbol: str,
        interval: str,
        candles: int | None = None,
        initial_cash: Decimal | None = None,
    ) -> BacktestRunResult:
        if candles is not None and candles <= 0:
            raise ValueError("candles must be > 0")
        if initial_cash is not None and initial_cash <= 0:
            raise ValueError("initial_cash must be > 0")

        strategy = get_strategy(strategy_name)
        normalized_symbol = symbol.upper()
        normalized_interval = interval.strip()
        candles_requested = candles if candles is not None else self.settings.strategy_default_candle_limit
        requested_initial_cash = initial_cash or self.settings.paper_initial_balance_usdt

        session_id = self._create_session(
            strategy_name=strategy.name,
            strategy_version=strategy.version,
            symbol=normalized_symbol,
            interval=normalized_interval,
            candles_requested=candles_requested,
            initial_cash=requested_initial_cash,
        )
        self._mark_running(session_id)

        analysis_service = _RecordingAnalysisService(MarketAnalysisService(strategy=strategy))
        engine = self._build_engine(analysis_service=analysis_service, initial_cash=requested_initial_cash)

        try:
            candle_rows = self._load_candles(
                analysis_service=analysis_service,
                symbol=normalized_symbol,
                interval=normalized_interval,
                candles_requested=candles_requested,
            )
            result = engine.run(symbol=normalized_symbol, interval=normalized_interval, candles=candle_rows)
            self._mark_completed(
                session_id=session_id,
                candles_used=result.candles_used,
                initial_cash=requested_initial_cash,
                final_equity=result.final_balance,
            )
            self._store_success_metric(
                session_id=session_id,
                requested_initial_cash=requested_initial_cash,
                result=result,
                stats=analysis_service.stats,
            )
            with session_scope() as session:
                report = BacktestPerformanceService(session).save_or_update_metrics(session_id)
            return BacktestRunResult(
                session_id=session_id,
                status=BACKTEST_STATUS_COMPLETED,
                strategy_name=strategy.name,
                symbol=normalized_symbol,
                interval=normalized_interval,
                candles_used=report.candles_used,
                total_pnl=report.equity_metrics.total_pnl,
                return_pct=report.equity_metrics.return_pct,
                data_quality=report.equity_metrics.data_quality,
                last_error=None,
            )
        except Exception as exc:
            self._mark_failed(session_id, exc)
            self._store_failure_metric(session_id, str(exc))
            try:
                with session_scope() as session:
                    report = BacktestPerformanceService(session).save_or_update_metrics(session_id)
            except Exception:
                logger.exception("Failed to finalize backtest metrics for session %s", session_id)
                report = None
            return BacktestRunResult(
                session_id=session_id,
                status=BACKTEST_STATUS_FAILED,
                strategy_name=strategy.name,
                symbol=normalized_symbol,
                interval=normalized_interval,
                candles_used=None if report is None else report.candles_used,
                total_pnl=None if report is None else report.equity_metrics.total_pnl,
                return_pct=None if report is None else report.equity_metrics.return_pct,
                data_quality="UNAVAILABLE" if report is None else report.equity_metrics.data_quality,
                last_error=str(exc),
            )

    def _build_engine(
        self,
        *,
        analysis_service: _RecordingAnalysisService,
        initial_cash: Decimal,
    ) -> BacktestEngine:
        if self._engine is not None:
            return self._engine

        engine = BacktestEngine(analysis_service=analysis_service)
        engine.settings = engine.settings.model_copy(update={"paper_initial_balance_usdt": initial_cash})
        return engine

    @staticmethod
    def _create_session(
        *,
        strategy_name: str,
        strategy_version: str,
        symbol: str,
        interval: str,
        candles_requested: int | None,
        initial_cash: Decimal,
    ) -> int:
        now = datetime.now(UTC)
        with session_scope() as session:
            item = BacktestSession(
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                symbol=symbol,
                interval=interval,
                status=BACKTEST_STATUS_CREATED,
                candles_requested=candles_requested,
                initial_cash=initial_cash,
                created_at=now,
                updated_at=now,
            )
            session.add(item)
            session.flush()
            return item.id

    @staticmethod
    def _mark_running(session_id: int) -> None:
        now = datetime.now(UTC)
        with session_scope() as session:
            item = session.get(BacktestSession, session_id)
            assert item is not None
            item.status = BACKTEST_STATUS_RUNNING
            item.started_at = now
            item.updated_at = now

    @staticmethod
    def _mark_completed(
        session_id: int,
        *,
        candles_used: int,
        initial_cash: Decimal,
        final_equity: Decimal,
    ) -> None:
        now = datetime.now(UTC)
        with session_scope() as session:
            item = session.get(BacktestSession, session_id)
            assert item is not None
            item.status = BACKTEST_STATUS_COMPLETED
            item.candles_used = candles_used
            item.initial_cash = initial_cash
            item.final_equity = final_equity
            item.finished_at = now
            item.updated_at = now
            item.last_error = None

    @staticmethod
    def _mark_failed(session_id: int, error: Exception) -> None:
        now = datetime.now(UTC)
        with session_scope() as session:
            item = session.get(BacktestSession, session_id)
            assert item is not None
            item.status = BACKTEST_STATUS_FAILED
            item.last_error = str(error)
            item.finished_at = now
            item.updated_at = now

    @staticmethod
    def _load_candles(
        *,
        analysis_service: _RecordingAnalysisService,
        symbol: str,
        interval: str,
        candles_requested: int,
    ):
        with session_scope() as session:
            candles = analysis_service.load_candles(
                session=session,
                symbol=symbol,
                interval=interval,
                limit=candles_requested,
            )
        if not candles:
            raise ValueError("No candles found in the database for selected symbol and interval.")
        return candles

    @staticmethod
    def _store_success_metric(
        *,
        session_id: int,
        requested_initial_cash: Decimal,
        result: BacktestResult,
        stats: _RecordedDecisionStats,
    ) -> None:
        skipped_count = max(
            (stats.buy + stats.sell) - (result.total_trades * 2),
            0,
        )
        with session_scope() as session:
            metric = session.execute(
                select(BacktestSessionMetric).where(BacktestSessionMetric.backtest_session_id == session_id)
            ).scalar_one_or_none()
            if metric is None:
                metric = BacktestSessionMetric(backtest_session_id=session_id)
                session.add(metric)

            metric.candles_used = result.candles_used
            metric.strategy_buy_count = stats.buy
            metric.strategy_sell_count = stats.sell
            metric.strategy_hold_count = stats.hold
            metric.executed_buy_count = result.total_trades
            metric.executed_sell_count = result.total_trades
            metric.skipped_count = skipped_count
            metric.total_trades = result.total_trades
            metric.winning_trades = result.winning_trades
            metric.losing_trades = result.losing_trades
            metric.win_rate = result.winrate_pct
            metric.initial_cash = requested_initial_cash
            metric.final_equity = result.final_balance
            metric.realized_pnl = result.total_pnl
            metric.unrealized_pnl = Decimal("0")
            metric.total_pnl = result.total_pnl
            metric.return_pct = result.total_pnl_pct
            metric.max_drawdown = result.max_drawdown_pct
            metric.average_confidence = None
            metric.min_confidence = None
            metric.max_confidence = None
            metric.data_quality = "COMPLETE"
            metric.unavailable_reason = None

    @staticmethod
    def _store_failure_metric(session_id: int, error_text: str) -> None:
        try:
            with session_scope() as session:
                metric = session.execute(
                    select(BacktestSessionMetric).where(BacktestSessionMetric.backtest_session_id == session_id)
                ).scalar_one_or_none()
                if metric is None:
                    metric = BacktestSessionMetric(backtest_session_id=session_id)
                    session.add(metric)
                metric.data_quality = "UNAVAILABLE"
                metric.unavailable_reason = error_text
        except Exception:
            logger.exception("Failed to persist partial backtest metrics for session %s", session_id)
