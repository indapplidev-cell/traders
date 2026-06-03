from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select

from app.analytics.paper_portfolio_analytics import PaperPortfolioAnalyticsService
from app.db.models import (
    RunnerSession,
    RuntimeTick,
    TradeDecisionRecord,
    RunnerSessionMetric,
)
from app.db.session import session_scope


@dataclass(slots=True)
class ActionCounts:
    buy: int = 0
    sell: int = 0
    hold: int = 0
    unknown: int = 0


@dataclass(slots=True)
class RiskMetrics:
    approved_count: int
    rejected_count: int
    approval_rate: float
    rejection_rate: float
    rejection_reasons: dict[str, int]


@dataclass(slots=True)
class ExecutionMetrics:
    executed_count: int
    skipped_count: int
    buy_executed_count: int
    sell_executed_count: int
    hold_or_noop_count: int
    execution_actions: dict[str, int]


@dataclass(slots=True)
class ConfidenceMetrics:
    count: int
    average: Decimal | None
    minimum: Decimal | None
    maximum: Decimal | None


@dataclass(slots=True)
class RuntimeQualityMetrics:
    ticks_requested: int
    ticks_completed: int
    audit_ticks_count: int
    error_ticks_count: int
    success_rate: float
    duration_seconds: float
    average_tick_duration_seconds: float | None


@dataclass(slots=True)
class MarketRegimeMetrics:
    regimes: dict[str, int]


@dataclass(slots=True)
class SessionPerformanceReport:
    session_id: int
    status: str
    strategy_name: str
    strategy_version: str
    symbol: str
    interval: str
    started_at: datetime | None
    stopped_at: datetime | None
    runtime_quality: RuntimeQualityMetrics
    strategy_action_counts: ActionCounts
    final_action_counts: ActionCounts
    risk_metrics: RiskMetrics
    execution_metrics: ExecutionMetrics
    confidence_metrics: ConfidenceMetrics
    market_regime_metrics: MarketRegimeMetrics
    candles_used_min: int | None
    candles_used_max: int | None
    candles_used_average: float | None
    journal_ids: list[int]
    errors: list[str]


@dataclass(slots=True)
class SessionPerformanceSummary:
    session_id: int
    status: str
    strategy_name: str
    symbol: str
    interval: str
    ticks_completed: int
    risk_rejection_rate: float
    execution_skipped_count: int
    average_confidence: Decimal | None
    error_ticks_count: int
    total_pnl: Decimal | None
    return_pct: Decimal | None
    data_quality: str | None


@dataclass(slots=True)
class SessionComparison:
    session_id: int
    status: str
    strategy_name: str
    symbol: str
    interval: str
    ticks_completed: int
    final_buy_count: int
    final_sell_count: int
    final_hold_count: int
    risk_rejection_rate: float
    execution_skipped_count: int
    average_confidence: Decimal | None
    total_pnl: Decimal | None
    return_pct: Decimal | None
    data_quality: str | None


class StrategyPerformanceService:
    """Сервис агрегации метрик по запуску bounded paper runner session."""

    def get_session_performance(self, session_id: int) -> SessionPerformanceReport:
        with session_scope() as session:
            runner_session = session.get(RunnerSession, session_id)
            if runner_session is None:
                raise ValueError(f"Runner session {session_id} not found.")

            ticks = list(
                session.execute(
                    select(RuntimeTick)
                    .where(RuntimeTick.runner_session_id == session_id)
                    .order_by(RuntimeTick.tick_number.asc(), RuntimeTick.id.asc())
                )
                .scalars()
                .all()
            )

            return self._build_report(runner_session, ticks, session)

    def list_session_performance(self, limit: int = 10) -> list[SessionPerformanceSummary]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        with session_scope() as session:
            sessions = list(
                session.execute(
                    select(RunnerSession)
                    .order_by(RunnerSession.created_at.desc(), RunnerSession.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            session_ids = [item.id for item in sessions]
            metrics_map = self._load_metrics_for_sessions(session, session_ids)

        return [
            self._build_summary(self.get_session_performance(item.id), metrics_map.get(item.id))
            for item in sessions
        ]

    def compare_sessions(
        self,
        strategy_name: str | None = None,
        symbol: str | None = None,
        limit: int = 10,
    ) -> list[SessionComparison]:
        if limit <= 0:
            raise ValueError("limit must be > 0")

        with session_scope() as session:
            query = select(RunnerSession)
            if strategy_name is not None:
                query = query.where(RunnerSession.strategy_name == strategy_name)
            if symbol is not None:
                query = query.where(RunnerSession.symbol == symbol.upper())
            sessions = list(
                session.execute(
                    query.order_by(RunnerSession.created_at.desc(), RunnerSession.id.desc()).limit(limit)
                )
                .scalars()
                .all()
            )
            session_ids = [item.id for item in sessions]
            metrics_map = self._load_metrics_for_sessions(session, session_ids)

        return [
            self._build_comparison(self.get_session_performance(item.id), metrics_map.get(item.id))
            for item in sessions
        ]

    def persist_session_metrics(self, session_id: int, symbol: str) -> RunnerSessionMetric:
        report = self.get_session_performance(session_id)
        portfolio = PaperPortfolioAnalyticsService().analyze_symbol(symbol)

        with session_scope() as session:
            metric = session.execute(
                select(RunnerSessionMetric)
                .where(RunnerSessionMetric.runner_session_id == session_id)
            ).scalar_one_or_none()

            if metric is None:
                metric = RunnerSessionMetric(
                    runner_session_id=session_id,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                session.add(metric)

            metric.ticks_requested = report.runtime_quality.ticks_requested
            metric.ticks_completed = report.runtime_quality.ticks_completed
            metric.audit_ticks_count = report.runtime_quality.audit_ticks_count
            metric.error_ticks_count = report.runtime_quality.error_ticks_count
            metric.success_rate = report.runtime_quality.success_rate
            metric.strategy_buy_count = report.strategy_action_counts.buy
            metric.strategy_sell_count = report.strategy_action_counts.sell
            metric.strategy_hold_count = report.strategy_action_counts.hold
            metric.final_buy_count = report.final_action_counts.buy
            metric.final_sell_count = report.final_action_counts.sell
            metric.final_hold_count = report.final_action_counts.hold
            metric.risk_approved_count = report.risk_metrics.approved_count
            metric.risk_rejected_count = report.risk_metrics.rejected_count
            metric.risk_rejection_rate = report.risk_metrics.rejection_rate
            metric.execution_executed_count = report.execution_metrics.executed_count
            metric.execution_skipped_count = report.execution_metrics.skipped_count
            metric.average_confidence = report.confidence_metrics.average
            metric.min_confidence = report.confidence_metrics.minimum
            metric.max_confidence = report.confidence_metrics.maximum
            metric.candles_used_min = report.candles_used_min
            metric.candles_used_max = report.candles_used_max
            metric.candles_used_average = report.candles_used_average
            metric.realized_pnl = portfolio.realized_pnl
            metric.unrealized_pnl = portfolio.unrealized_pnl
            metric.total_pnl = portfolio.total_pnl
            metric.return_pct = portfolio.return_pct
            metric.data_quality = portfolio.data_quality
            metric.unavailable_reason = portfolio.unavailable_reason
            metric.updated_at = datetime.now(UTC)
            session.flush()
            return metric

    @staticmethod
    def _build_report(
        runner_session: RunnerSession,
        ticks: list[RuntimeTick],
        session,
    ) -> SessionPerformanceReport:
        runtime_quality = StrategyPerformanceService._build_runtime_quality(runner_session, ticks)
        strategy_action_counts = StrategyPerformanceService._count_actions(
            tick.strategy_action for tick in ticks
        )
        final_action_counts = StrategyPerformanceService._count_actions(
            tick.final_action for tick in ticks
        )
        risk_metrics = StrategyPerformanceService._build_risk_metrics(ticks)
        execution_metrics = StrategyPerformanceService._build_execution_metrics(ticks)
        confidence_metrics = StrategyPerformanceService._build_confidence_metrics(session, ticks)
        market_regime_metrics = StrategyPerformanceService._build_market_regime_metrics(ticks)
        candles_used_min, candles_used_max, candles_used_average = StrategyPerformanceService._build_candles_used(ticks)
        journal_ids = StrategyPerformanceService._build_journal_ids(ticks)
        errors = StrategyPerformanceService._build_errors(ticks)

        return SessionPerformanceReport(
            session_id=runner_session.id,
            status=runner_session.status,
            strategy_name=runner_session.strategy_name,
            strategy_version=runner_session.strategy_version,
            symbol=runner_session.symbol,
            interval=runner_session.interval,
            started_at=runner_session.started_at,
            stopped_at=runner_session.stopped_at,
            runtime_quality=runtime_quality,
            strategy_action_counts=strategy_action_counts,
            final_action_counts=final_action_counts,
            risk_metrics=risk_metrics,
            execution_metrics=execution_metrics,
            confidence_metrics=confidence_metrics,
            market_regime_metrics=market_regime_metrics,
            candles_used_min=candles_used_min,
            candles_used_max=candles_used_max,
            candles_used_average=candles_used_average,
            journal_ids=journal_ids,
            errors=errors,
        )

    @staticmethod
    def _count_actions(actions: Iterable[str]) -> ActionCounts:
        counts = ActionCounts()
        for action in actions:
            if action == "BUY":
                counts.buy += 1
            elif action == "SELL":
                counts.sell += 1
            elif action == "HOLD":
                counts.hold += 1
            else:
                counts.unknown += 1
        return counts

    @staticmethod
    def _build_risk_metrics(ticks: list[RuntimeTick]) -> RiskMetrics:
        approved_count = sum(1 for tick in ticks if tick.risk_approved)
        rejected_count = len(ticks) - approved_count
        rejection_reasons: dict[str, int] = {}
        for tick in ticks:
            if not tick.risk_approved:
                reason = tick.risk_reason or "unknown"
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        audit_count = len(ticks)
        return RiskMetrics(
            approved_count=approved_count,
            rejected_count=rejected_count,
            approval_rate=(approved_count / audit_count if audit_count else 0.0),
            rejection_rate=(rejected_count / audit_count if audit_count else 0.0),
            rejection_reasons=rejection_reasons,
        )

    @staticmethod
    def _build_execution_metrics(ticks: list[RuntimeTick]) -> ExecutionMetrics:
        execution_actions: dict[str, int] = {}
        for tick in ticks:
            execution_actions[tick.execution_action] = execution_actions.get(tick.execution_action, 0) + 1

        executed_count = sum(
            count
            for action, count in execution_actions.items()
            if action not in {"HOLD", "SKIPPED", "ERROR"}
        )
        skipped_count = execution_actions.get("SKIPPED", 0)
        buy_executed_count = execution_actions.get("BUY", 0)
        sell_executed_count = execution_actions.get("SELL", 0)
        hold_or_noop_count = execution_actions.get("HOLD", 0) + skipped_count
        return ExecutionMetrics(
            executed_count=executed_count,
            skipped_count=skipped_count,
            buy_executed_count=buy_executed_count,
            sell_executed_count=sell_executed_count,
            hold_or_noop_count=hold_or_noop_count,
            execution_actions=execution_actions,
        )

    @staticmethod
    def _build_confidence_metrics(session, ticks: list[RuntimeTick]) -> ConfidenceMetrics:
        journal_ids = [tick.journal_id for tick in ticks if tick.journal_id is not None]
        if not journal_ids:
            return ConfidenceMetrics(count=0, average=None, minimum=None, maximum=None)

        rows = session.execute(
            select(TradeDecisionRecord.confidence)
            .where(TradeDecisionRecord.id.in_(journal_ids))
        ).scalars().all()
        values = [Decimal(str(value)) for value in rows if value is not None]
        if not values:
            return ConfidenceMetrics(count=0, average=None, minimum=None, maximum=None)

        average = sum(values) / Decimal(len(values))
        return ConfidenceMetrics(
            count=len(values),
            average=average,
            minimum=min(values),
            maximum=max(values),
        )

    @staticmethod
    def _build_market_regime_metrics(ticks: list[RuntimeTick]) -> MarketRegimeMetrics:
        regimes: dict[str, int] = {}
        for tick in ticks:
            regime = tick.market_regime or "unknown"
            regimes[regime] = regimes.get(regime, 0) + 1
        return MarketRegimeMetrics(regimes=regimes)

    @staticmethod
    def _build_candles_used(ticks: list[RuntimeTick]) -> tuple[int | None, int | None, float | None]:
        values = [tick.candles_used for tick in ticks if tick.candles_used is not None]
        if not values:
            return None, None, None
        return min(values), max(values), sum(values) / len(values)

    @staticmethod
    def _build_journal_ids(ticks: list[RuntimeTick]) -> list[int]:
        return sorted({tick.journal_id for tick in ticks if tick.journal_id is not None})

    @staticmethod
    def _build_errors(ticks: list[RuntimeTick]) -> list[str]:
        return [tick.error for tick in ticks if tick.error is not None]

    @staticmethod
    def _build_runtime_quality(runner_session: RunnerSession, ticks: list[RuntimeTick]) -> RuntimeQualityMetrics:
        error_ticks_count = sum(1 for tick in ticks if tick.error is not None)
        duration_seconds = sum(
            (tick.finished_at - tick.started_at).total_seconds()
            for tick in ticks
            if tick.finished_at is not None and tick.started_at is not None
        )
        average_tick_duration_seconds = (
            duration_seconds / len(ticks) if ticks else None
        )
        return RuntimeQualityMetrics(
            ticks_requested=runner_session.ticks_requested,
            ticks_completed=runner_session.ticks_completed,
            audit_ticks_count=len(ticks),
            error_ticks_count=error_ticks_count,
            success_rate=(runner_session.ticks_completed / runner_session.ticks_requested if runner_session.ticks_requested else 0.0),
            duration_seconds=duration_seconds,
            average_tick_duration_seconds=average_tick_duration_seconds,
        )

    @staticmethod
    def _load_metrics_for_sessions(session, session_ids: list[int]) -> dict[int, RunnerSessionMetric]:
        if not session_ids:
            return {}
        metrics = session.execute(
            select(RunnerSessionMetric).where(RunnerSessionMetric.runner_session_id.in_(session_ids))
        ).scalars().all()
        return {metric.runner_session_id: metric for metric in metrics}

    @staticmethod
    def _build_summary(
        report: SessionPerformanceReport,
        metric: RunnerSessionMetric | None = None,
    ) -> SessionPerformanceSummary:
        return SessionPerformanceSummary(
            session_id=report.session_id,
            status=report.status,
            strategy_name=report.strategy_name,
            symbol=report.symbol,
            interval=report.interval,
            ticks_completed=report.runtime_quality.ticks_completed,
            risk_rejection_rate=report.risk_metrics.rejection_rate,
            execution_skipped_count=report.execution_metrics.skipped_count,
            average_confidence=report.confidence_metrics.average,
            error_ticks_count=report.runtime_quality.error_ticks_count,
            total_pnl=metric.total_pnl if metric is not None else None,
            return_pct=metric.return_pct if metric is not None else None,
            data_quality=metric.data_quality if metric is not None else None,
        )

    @staticmethod
    def _build_comparison(
        report: SessionPerformanceReport,
        metric: RunnerSessionMetric | None = None,
    ) -> SessionComparison:
        return SessionComparison(
            session_id=report.session_id,
            status=report.status,
            strategy_name=report.strategy_name,
            symbol=report.symbol,
            interval=report.interval,
            ticks_completed=report.runtime_quality.ticks_completed,
            final_buy_count=report.final_action_counts.buy,
            final_sell_count=report.final_action_counts.sell,
            final_hold_count=report.final_action_counts.hold,
            risk_rejection_rate=report.risk_metrics.rejection_rate,
            execution_skipped_count=report.execution_metrics.skipped_count,
            average_confidence=report.confidence_metrics.average,
            total_pnl=metric.total_pnl if metric is not None else None,
            return_pct=metric.return_pct if metric is not None else None,
            data_quality=metric.data_quality if metric is not None else None,
        )
