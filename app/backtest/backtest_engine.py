"""Исторический backtest без использования реального paper account."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from app.backtest.backtest_portfolio import BacktestPortfolio
from app.backtest.backtest_result import BacktestResult
from app.config.settings import get_settings
from app.db.models import Candle
from app.execution.protective_levels import detect_long_protective_exit
from app.market.analysis_service import MarketAnalysisService
from app.market.indicator_service import IndicatorCalculationError, IndicatorService
from app.risk.risk_manager import RiskManager
from app.strategy.trade_decision import DecisionType, TradeDecision


class BacktestEngine:
    """Прогоняет стратегию по историческим свечам без будущих данных."""

    def __init__(
        self,
        analysis_service: MarketAnalysisService | None = None,
        risk_manager: RiskManager | None = None,
    ) -> None:
        self.settings = get_settings()
        self.analysis_service = analysis_service or MarketAnalysisService()
        self.risk_manager = risk_manager or RiskManager()

    def load_candles_from_db(
        self,
        *,
        session: Session,
        symbol: str,
        interval: str,
        days: int,
    ) -> list[Candle]:
        """Читает из БД историю за последние N дней для отдельного режима backtest."""

        if days <= 0:
            raise ValueError("Параметр days должен быть положительным целым числом.")

        since = datetime.now(UTC) - timedelta(days=days)
        candles = self.analysis_service.load_candles_since(
            session=session,
            symbol=symbol,
            interval=interval,
            since=since,
        )
        if not candles:
            raise ValueError("В БД нет свечей для выбранного диапазона. Сначала выполните load-history.")
        return candles

    def run(self, *, symbol: str, interval: str, candles: Sequence[Candle]) -> BacktestResult:
        """Запускает backtest на последовательности закрытых свечей.

        Модель исполнения намеренно грубая: используется только OHLC свечи,
        без внутрисвечного порядка цен и без проскальзывания. Если в одной
        свече задеты и SL, и TP, выбирается stop-loss как консервативный вариант.
        """

        candle_list = list(candles)
        if len(candle_list) < IndicatorService.MIN_CANDLES:
            raise IndicatorCalculationError(
                f"Недостаточно свечей для backtest: нужно минимум {IndicatorService.MIN_CANDLES}, "
                f"получено {len(candle_list)}."
            )

        portfolio = BacktestPortfolio(self.settings)
        initial_balance = portfolio.initial_balance
        equity_curve: list[Decimal] = [initial_balance]

        for index in range(IndicatorService.MIN_CANDLES - 1, len(candle_list)):
            window = candle_list[: index + 1]
            analysis = self.analysis_service.analyze(symbol=symbol, interval=interval, candles=window)
            current_candle = analysis.latest_candle

            if portfolio.open_position is not None:
                protective_hit = detect_long_protective_exit(
                    candle=current_candle,
                    stop_loss=portfolio.open_position.stop_loss,
                    take_profit=portfolio.open_position.take_profit,
                )
                if protective_hit is not None:
                    action, exit_price = protective_hit
                    portfolio.close_position(
                        exit_price=exit_price,
                        exit_action=action,
                        closed_at=current_candle.close_time,
                    )
                    equity_curve.append(portfolio.balance)
                    continue

            strategy_decision = TradeDecision.build(
                symbol=analysis.strategy_decision.symbol,
                interval=analysis.strategy_decision.interval,
                decision=analysis.strategy_decision.decision,
                reason=analysis.strategy_decision.reason,
                regime=analysis.strategy_decision.regime,
                price=analysis.strategy_decision.price,
                created_at=current_candle.close_time,
            )
            risk_result = self.risk_manager.validate_decision(strategy_decision, portfolio.build_risk_state())

            if portfolio.open_position is not None and strategy_decision.decision == DecisionType.SELL:
                portfolio.close_position(
                    exit_price=current_candle.close,
                    exit_action="SELL",
                    closed_at=current_candle.close_time,
                )
            elif portfolio.open_position is None and strategy_decision.decision == DecisionType.BUY and risk_result.approved:
                portfolio.open_long(
                    symbol=symbol,
                    entry_price=current_candle.close,
                    atr_14=analysis.indicator_snapshot.atr_14,
                    opened_at=current_candle.close_time,
                )

            equity_curve.append(portfolio.mark_to_market(close_price=current_candle.close))

        if portfolio.open_position is not None:
            last_candle = candle_list[-1]
            portfolio.close_position(
                exit_price=last_candle.close,
                exit_action="END_OF_TEST",
                closed_at=last_candle.close_time,
            )
            equity_curve.append(portfolio.balance)

        final_balance = portfolio.balance
        total_pnl = final_balance - initial_balance
        total_trades = len(portfolio.closed_trades)
        winning_trades = sum(1 for trade in portfolio.closed_trades if trade.pnl > 0)
        losing_trades = sum(1 for trade in portfolio.closed_trades if trade.pnl < 0)
        winrate_pct = (
            (Decimal(winning_trades) / Decimal(total_trades) * Decimal("100"))
            if total_trades > 0
            else Decimal("0")
        )

        return BacktestResult(
            symbol=symbol.upper(),
            interval=interval,
            candles_used=len(candle_list),
            initial_balance=initial_balance,
            final_balance=final_balance,
            total_pnl=total_pnl,
            total_pnl_pct=(total_pnl / initial_balance * Decimal("100")) if initial_balance > 0 else Decimal("0"),
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            winrate_pct=winrate_pct,
            max_drawdown_pct=self._calculate_max_drawdown_pct(equity_curve),
            largest_win=max((trade.pnl for trade in portfolio.closed_trades), default=Decimal("0")),
            largest_loss=min((trade.pnl for trade in portfolio.closed_trades), default=Decimal("0")),
            trades=portfolio.closed_trades,
        )

    @staticmethod
    def _calculate_max_drawdown_pct(equity_curve: Sequence[Decimal]) -> Decimal:
        """Считает максимальную просадку по equity curve."""

        if not equity_curve:
            return Decimal("0")

        peak = equity_curve[0]
        max_drawdown = Decimal("0")
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            if peak > 0:
                drawdown = (peak - equity) / peak * Decimal("100")
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        return max_drawdown
