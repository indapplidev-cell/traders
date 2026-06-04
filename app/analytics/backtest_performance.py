"""Backtest performance analytics service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestSession, BacktestSessionMetric


@dataclass(slots=True)
class BacktestActionCounts:
    buy: int
    sell: int
    hold: int
    unknown: int


@dataclass(slots=True)
class BacktestTradeMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal | None
    executed_buy_count: int
    executed_sell_count: int
    skipped_count: int


@dataclass(slots=True)
class BacktestEquityMetrics:
    initial_cash: Decimal | None
    final_equity: Decimal | None
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    total_pnl: Decimal | None
    return_pct: Decimal | None
    max_drawdown: Decimal | None
    data_quality: str
    unavailable_reason: str | None


@dataclass(slots=True)
class BacktestPerformanceReport:
    session_id: int
    status: str
    strategy_name: str
    strategy_version: str
    symbol: str
    interval: str
    started_at: datetime | None
    finished_at: datetime | None
    candles_used: int | None
    action_counts: BacktestActionCounts
    trade_metrics: BacktestTradeMetrics
    equity_metrics: BacktestEquityMetrics
    average_confidence: Decimal | None
    min_confidence: Decimal | None
    max_confidence: Decimal | None
    errors: list[str]


@dataclass(slots=True)
class BacktestPerformanceSummary:
    session_id: int
    status: str
    strategy_name: str
    symbol: str
    interval: str
    candles_used: int | None
    total_trades: int | None
    win_rate: Decimal | None
    total_pnl: Decimal | None
    return_pct: Decimal | None
    max_drawdown: Decimal | None
    data_quality: str


class BacktestPerformanceService:
    """Read and persist backtest session analytics."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_backtest_performance(self, session_id: int) -> BacktestPerformanceReport:
        backtest_session = self._get_session(session_id)
        metric = self._get_metric(session_id)

        if metric is None:
            return self._build_report_without_metrics(backtest_session)

        return self._build_report(backtest_session, metric)

    def list_backtest_performance(self, limit: int = 10) -> list[BacktestPerformanceSummary]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        sessions = self.session.execute(
            select(BacktestSession).order_by(BacktestSession.created_at.desc(), BacktestSession.id.desc()).limit(limit)
        ).scalars().all()

        results: list[BacktestPerformanceSummary] = []
        for item in sessions:
            metric = self._get_metric(item.id)
            results.append(
                BacktestPerformanceSummary(
                    session_id=item.id,
                    status=item.status,
                    strategy_name=item.strategy_name,
                    symbol=item.symbol,
                    interval=item.interval,
                    candles_used=item.candles_used,
                    total_trades=None if metric is None else metric.total_trades,
                    win_rate=None if metric is None else metric.win_rate,
                    total_pnl=None if metric is None else metric.total_pnl,
                    return_pct=None if metric is None else metric.return_pct,
                    max_drawdown=None if metric is None else metric.max_drawdown,
                    data_quality="UNAVAILABLE" if metric is None else metric.data_quality,
                )
            )
        return results

    def save_or_update_metrics(self, session_id: int) -> BacktestPerformanceReport:
        backtest_session = self._get_session(session_id)
        metric = self._get_metric(session_id)

        if metric is None:
            metric = BacktestSessionMetric(backtest_session_id=session_id)
            self.session.add(metric)

        metric.candles_used = self._coalesce_int(metric.candles_used, backtest_session.candles_used)
        metric.strategy_buy_count = self._coalesce_int(metric.strategy_buy_count, 0)
        metric.strategy_sell_count = self._coalesce_int(metric.strategy_sell_count, 0)
        metric.strategy_hold_count = self._coalesce_int(metric.strategy_hold_count, 0)
        metric.executed_buy_count = self._coalesce_int(metric.executed_buy_count, 0)
        metric.executed_sell_count = self._coalesce_int(metric.executed_sell_count, 0)
        metric.skipped_count = self._coalesce_int(metric.skipped_count, 0)
        metric.total_trades = self._coalesce_int(metric.total_trades, 0)
        metric.winning_trades = self._coalesce_int(metric.winning_trades, 0)
        metric.losing_trades = self._coalesce_int(metric.losing_trades, 0)
        metric.initial_cash = self._coalesce_decimal(metric.initial_cash, backtest_session.initial_cash)
        metric.final_equity = self._coalesce_decimal(metric.final_equity, backtest_session.final_equity)

        if metric.total_pnl is None and metric.initial_cash is not None and metric.final_equity is not None:
            metric.total_pnl = metric.final_equity - metric.initial_cash
        if metric.realized_pnl is None:
            metric.realized_pnl = metric.total_pnl
        if metric.return_pct is None and metric.total_pnl is not None and metric.initial_cash not in {None, Decimal("0")}:
            metric.return_pct = (metric.total_pnl / metric.initial_cash) * Decimal("100")
        if metric.win_rate is None and metric.total_trades and metric.total_trades > 0:
            metric.win_rate = (Decimal(metric.winning_trades or 0) / Decimal(metric.total_trades)) * Decimal("100")

        data_quality, unavailable_reason = self._resolve_data_quality(metric)
        metric.data_quality = data_quality
        metric.unavailable_reason = unavailable_reason

        self.session.flush()
        return self._build_report(backtest_session, metric)

    def _get_session(self, session_id: int) -> BacktestSession:
        item = self.session.get(BacktestSession, session_id)
        if item is None:
            raise ValueError(f"Backtest session {session_id} not found")
        return item

    def _get_metric(self, session_id: int) -> BacktestSessionMetric | None:
        return self.session.execute(
            select(BacktestSessionMetric).where(BacktestSessionMetric.backtest_session_id == session_id)
        ).scalar_one_or_none()

    @staticmethod
    def _coalesce_int(current: int | None, fallback: int | None) -> int | None:
        return current if current is not None else fallback

    @staticmethod
    def _coalesce_decimal(current: Decimal | None, fallback: Decimal | None) -> Decimal | None:
        return current if current is not None else fallback

    @staticmethod
    def _resolve_data_quality(metric: BacktestSessionMetric) -> tuple[str, str | None]:
        if metric.unavailable_reason:
            return "UNAVAILABLE", metric.unavailable_reason
        if metric.total_pnl is not None and metric.return_pct is not None:
            return "COMPLETE", None
        if metric.initial_cash is not None or metric.final_equity is not None:
            return "PARTIAL", "PnL metrics are incomplete"
        return "UNAVAILABLE", "No metrics recorded"

    @staticmethod
    def _build_report_without_metrics(backtest_session: BacktestSession) -> BacktestPerformanceReport:
        return BacktestPerformanceReport(
            session_id=backtest_session.id,
            status=backtest_session.status,
            strategy_name=backtest_session.strategy_name,
            strategy_version=backtest_session.strategy_version,
            symbol=backtest_session.symbol,
            interval=backtest_session.interval,
            started_at=backtest_session.started_at,
            finished_at=backtest_session.finished_at,
            candles_used=backtest_session.candles_used,
            action_counts=BacktestActionCounts(buy=0, sell=0, hold=0, unknown=0),
            trade_metrics=BacktestTradeMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=None,
                executed_buy_count=0,
                executed_sell_count=0,
                skipped_count=0,
            ),
            equity_metrics=BacktestEquityMetrics(
                initial_cash=backtest_session.initial_cash,
                final_equity=backtest_session.final_equity,
                realized_pnl=None,
                unrealized_pnl=None,
                total_pnl=None,
                return_pct=None,
                max_drawdown=None,
                data_quality="UNAVAILABLE",
                unavailable_reason="No metrics recorded",
            ),
            average_confidence=None,
            min_confidence=None,
            max_confidence=None,
            errors=[backtest_session.last_error] if backtest_session.last_error else [],
        )

    @staticmethod
    def _build_report(
        backtest_session: BacktestSession,
        metric: BacktestSessionMetric,
    ) -> BacktestPerformanceReport:
        return BacktestPerformanceReport(
            session_id=backtest_session.id,
            status=backtest_session.status,
            strategy_name=backtest_session.strategy_name,
            strategy_version=backtest_session.strategy_version,
            symbol=backtest_session.symbol,
            interval=backtest_session.interval,
            started_at=backtest_session.started_at,
            finished_at=backtest_session.finished_at,
            candles_used=metric.candles_used if metric.candles_used is not None else backtest_session.candles_used,
            action_counts=BacktestActionCounts(
                buy=metric.strategy_buy_count or 0,
                sell=metric.strategy_sell_count or 0,
                hold=metric.strategy_hold_count or 0,
                unknown=0,
            ),
            trade_metrics=BacktestTradeMetrics(
                total_trades=metric.total_trades or 0,
                winning_trades=metric.winning_trades or 0,
                losing_trades=metric.losing_trades or 0,
                win_rate=metric.win_rate,
                executed_buy_count=metric.executed_buy_count or 0,
                executed_sell_count=metric.executed_sell_count or 0,
                skipped_count=metric.skipped_count or 0,
            ),
            equity_metrics=BacktestEquityMetrics(
                initial_cash=metric.initial_cash,
                final_equity=metric.final_equity,
                realized_pnl=metric.realized_pnl,
                unrealized_pnl=metric.unrealized_pnl,
                total_pnl=metric.total_pnl,
                return_pct=metric.return_pct,
                max_drawdown=metric.max_drawdown,
                data_quality=metric.data_quality,
                unavailable_reason=metric.unavailable_reason,
            ),
            average_confidence=metric.average_confidence,
            min_confidence=metric.min_confidence,
            max_confidence=metric.max_confidence,
            errors=[backtest_session.last_error] if backtest_session.last_error else [],
        )
