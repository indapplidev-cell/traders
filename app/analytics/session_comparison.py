"""Comparison service for runner and backtest session analytics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BacktestSession, BacktestSessionMetric, RunnerSession, RunnerSessionMetric


@dataclass(slots=True)
class ComparableSessionSummary:
    source_type: str
    session_id: int
    status: str
    strategy_name: str
    symbol: str
    interval: str
    ticks_or_candles: int | None
    risk_rejection_rate: Decimal | None
    execution_skipped_count: int | None
    average_confidence: Decimal | None
    total_pnl: Decimal | None
    return_pct: Decimal | None
    max_drawdown: Decimal | None
    data_quality: str


@dataclass(slots=True)
class SessionComparisonResult:
    left: ComparableSessionSummary
    right: ComparableSessionSummary
    same_strategy: bool
    same_symbol: bool
    same_interval: bool
    comparable: bool
    warnings: list[str]
    pnl_delta: Decimal | None
    return_pct_delta: Decimal | None
    confidence_delta: Decimal | None
    risk_rejection_delta: Decimal | None


class SessionComparisonService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def compare(
        self,
        left_type: str,
        left_id: int,
        right_type: str,
        right_id: int,
    ) -> SessionComparisonResult:
        left = self._load_summary(left_type, left_id)
        right = self._load_summary(right_type, right_id)

        warnings: list[str] = []
        same_strategy = left.strategy_name == right.strategy_name
        same_symbol = left.symbol == right.symbol
        same_interval = left.interval == right.interval
        comparable = True

        if not same_strategy:
            comparable = False
            warnings.append("Different strategies")
        if not same_symbol:
            comparable = False
            warnings.append("Different symbols")
        if not same_interval:
            comparable = False
            warnings.append("Different intervals")
        if left.data_quality == "UNAVAILABLE" or right.data_quality == "UNAVAILABLE":
            comparable = False
            warnings.append("Unavailable data quality")
        if left.source_type != right.source_type:
            warnings.append("RUNNER and BACKTEST are different execution modes")

        pnl_delta = self._delta_with_warning(left.total_pnl, right.total_pnl, "PnL delta unavailable", warnings)
        return_pct_delta = self._delta_with_warning(
            left.return_pct,
            right.return_pct,
            "Return pct delta unavailable",
            warnings,
        )

        return SessionComparisonResult(
            left=left,
            right=right,
            same_strategy=same_strategy,
            same_symbol=same_symbol,
            same_interval=same_interval,
            comparable=comparable,
            warnings=warnings,
            pnl_delta=pnl_delta,
            return_pct_delta=return_pct_delta,
            confidence_delta=self._delta_without_warning(left.average_confidence, right.average_confidence),
            risk_rejection_delta=self._delta_without_warning(left.risk_rejection_rate, right.risk_rejection_rate),
        )

    def _load_summary(self, source_type: str, session_id: int) -> ComparableSessionSummary:
        normalized_type = source_type.strip().lower()
        if normalized_type == "runner":
            return self._load_runner_summary(session_id)
        if normalized_type == "backtest":
            return self._load_backtest_summary(session_id)
        raise ValueError(f"Unsupported session type: {source_type}")

    def _load_runner_summary(self, session_id: int) -> ComparableSessionSummary:
        session_row = self.session.get(RunnerSession, session_id)
        if session_row is None:
            raise ValueError(f"Runner session {session_id} not found")

        metric = self.session.execute(
            select(RunnerSessionMetric).where(RunnerSessionMetric.runner_session_id == session_id)
        ).scalar_one_or_none()

        return ComparableSessionSummary(
            source_type="runner",
            session_id=session_row.id,
            status=session_row.status,
            strategy_name=session_row.strategy_name,
            symbol=session_row.symbol,
            interval=session_row.interval,
            ticks_or_candles=session_row.ticks_completed,
            risk_rejection_rate=None if metric is None else Decimal(str(metric.risk_rejection_rate)),
            execution_skipped_count=None if metric is None else metric.execution_skipped_count,
            average_confidence=None if metric is None else metric.average_confidence,
            total_pnl=None if metric is None else metric.total_pnl,
            return_pct=None if metric is None else metric.return_pct,
            max_drawdown=None,
            data_quality="UNAVAILABLE" if metric is None else metric.data_quality,
        )

    def _load_backtest_summary(self, session_id: int) -> ComparableSessionSummary:
        session_row = self.session.get(BacktestSession, session_id)
        if session_row is None:
            raise ValueError(f"Backtest session {session_id} not found")

        metric = self.session.execute(
            select(BacktestSessionMetric).where(BacktestSessionMetric.backtest_session_id == session_id)
        ).scalar_one_or_none()

        return ComparableSessionSummary(
            source_type="backtest",
            session_id=session_row.id,
            status=session_row.status,
            strategy_name=session_row.strategy_name,
            symbol=session_row.symbol,
            interval=session_row.interval,
            ticks_or_candles=session_row.candles_used,
            risk_rejection_rate=None,
            execution_skipped_count=None if metric is None else metric.skipped_count,
            average_confidence=None if metric is None else metric.average_confidence,
            total_pnl=None if metric is None else metric.total_pnl,
            return_pct=None if metric is None else metric.return_pct,
            max_drawdown=None if metric is None else metric.max_drawdown,
            data_quality="UNAVAILABLE" if metric is None else metric.data_quality,
        )

    @staticmethod
    def _delta_with_warning(
        left: Decimal | None,
        right: Decimal | None,
        warning: str,
        warnings: list[str],
    ) -> Decimal | None:
        if left is None or right is None:
            warnings.append(warning)
            return None
        return left - right

    @staticmethod
    def _delta_without_warning(left: Decimal | None, right: Decimal | None) -> Decimal | None:
        if left is None or right is None:
            return None
        return left - right
