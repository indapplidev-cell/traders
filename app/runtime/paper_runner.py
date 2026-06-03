"""Bounded paper runner sessions with runtime tick audit."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.analytics.strategy_performance import StrategyPerformanceService
from app.db.models import RunnerSession, RuntimeTick
from app.db.session import session_scope
from app.runtime.strategy_runtime import StrategyRuntime
from app.strategy.strategy_registry import get_strategy

logger = logging.getLogger(__name__)


RUNNER_STATUS_CREATED = "CREATED"
RUNNER_STATUS_RUNNING = "RUNNING"
RUNNER_STATUS_STOPPED = "STOPPED"
RUNNER_STATUS_FAILED = "FAILED"


@dataclass(slots=True)
class RunnerStartResult:
    """Результат bounded paper runner session."""

    session_id: int
    status: str
    strategy_name: str
    strategy_version: str
    symbol: str
    interval: str
    ticks_requested: int
    ticks_completed: int
    last_error: str | None


class PaperRunner:
    """Создаёт bounded runner session и пишет audit по каждому tick."""

    def __init__(self, *, runtime: StrategyRuntime | None = None) -> None:
        self.runtime = runtime or StrategyRuntime()

    def start(
        self,
        *,
        strategy_name: str,
        symbol: str,
        interval: str,
        ticks: int,
        sleep_seconds: float,
    ) -> RunnerStartResult:
        """Запускает bounded runner session и возвращает её итоговый результат."""

        self._validate_bounds(ticks=ticks, sleep_seconds=sleep_seconds)
        strategy = get_strategy(strategy_name)
        normalized_symbol = symbol.upper()

        with session_scope() as session:
            runner_session = RunnerSession(
                strategy_name=strategy.name,
                strategy_version=strategy.version,
                symbol=normalized_symbol,
                interval=interval,
                status=RUNNER_STATUS_CREATED,
                started_at=None,
                stopped_at=None,
                ticks_requested=ticks,
                ticks_completed=0,
                last_error=None,
            )
            session.add(runner_session)
            session.flush()
            session_id = runner_session.id

        self._mark_running(session_id)

        completed_ticks = 0
        try:
            for tick_number in range(1, ticks + 1):
                started_at = datetime.now(UTC)
                try:
                    result = self.runtime.run_tick(strategy_name, normalized_symbol, interval)
                except Exception as exc:
                    self._record_tick_error(
                        session_id=session_id,
                        tick_number=tick_number,
                        symbol=normalized_symbol,
                        interval=interval,
                        started_at=started_at,
                        error=exc,
                    )
                    self._mark_failed(session_id, completed_ticks=completed_ticks, error=exc)
                    self._persist_session_metrics(session_id, normalized_symbol)
                    return self._get_result(session_id)

                finished_at = datetime.now(UTC)
                self._record_tick_success(
                    session_id=session_id,
                    tick_number=tick_number,
                    started_at=started_at,
                    finished_at=finished_at,
                    result=result,
                )
                completed_ticks += 1
                self._update_ticks_completed(session_id, completed_ticks)

                if tick_number < ticks and sleep_seconds > 0:
                    time.sleep(sleep_seconds)

        except Exception as exc:
            self._mark_failed(session_id, completed_ticks=completed_ticks, error=exc)
            self._persist_session_metrics(session_id, normalized_symbol)
            return self._get_result(session_id)

        self._mark_stopped(session_id, completed_ticks=completed_ticks)
        self._persist_session_metrics(session_id, normalized_symbol)
        return self._get_result(session_id)

    def list_sessions(self, *, limit: int) -> list[RunnerSession]:
        """Возвращает последние runner sessions."""

        if limit <= 0:
            raise ValueError("limit must be > 0")

        with session_scope() as session:
            return list(
                session.execute(
                    select(RunnerSession)
                    .order_by(RunnerSession.created_at.desc(), RunnerSession.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )

    def list_ticks(self, *, session_id: int) -> list[RuntimeTick]:
        """Возвращает audit ticks для одной session."""

        with session_scope() as session:
            return list(
                session.execute(
                    select(RuntimeTick)
                    .where(RuntimeTick.runner_session_id == session_id)
                    .order_by(RuntimeTick.tick_number.asc(), RuntimeTick.id.asc())
                )
                .scalars()
                .all()
            )

    def _validate_bounds(self, *, ticks: int, sleep_seconds: float) -> None:
        settings = self.runtime.settings
        if ticks <= 0:
            raise ValueError("ticks must be > 0")
        if ticks > settings.strategy_max_ticks:
            raise ValueError(f"ticks must be <= STRATEGY_MAX_TICKS ({settings.strategy_max_ticks})")
        if sleep_seconds < 0:
            raise ValueError("sleep_seconds must be >= 0")

    @staticmethod
    def _mark_running(session_id: int) -> None:
        with session_scope() as session:
            runner_session = session.get(RunnerSession, session_id)
            assert runner_session is not None
            runner_session.status = RUNNER_STATUS_RUNNING
            runner_session.started_at = datetime.now(UTC)
            runner_session.updated_at = datetime.now(UTC)

    @staticmethod
    def _update_ticks_completed(session_id: int, ticks_completed: int) -> None:
        with session_scope() as session:
            runner_session = session.get(RunnerSession, session_id)
            assert runner_session is not None
            runner_session.ticks_completed = ticks_completed
            runner_session.updated_at = datetime.now(UTC)

    @staticmethod
    def _mark_stopped(session_id: int, *, completed_ticks: int) -> None:
        with session_scope() as session:
            runner_session = session.get(RunnerSession, session_id)
            assert runner_session is not None
            runner_session.status = RUNNER_STATUS_STOPPED
            runner_session.ticks_completed = completed_ticks
            runner_session.stopped_at = datetime.now(UTC)
            runner_session.last_error = None
            runner_session.updated_at = datetime.now(UTC)

    @staticmethod
    def _mark_failed(session_id: int, *, completed_ticks: int, error: Exception) -> None:
        with session_scope() as session:
            runner_session = session.get(RunnerSession, session_id)
            assert runner_session is not None
            runner_session.status = RUNNER_STATUS_FAILED
            runner_session.ticks_completed = completed_ticks
            runner_session.stopped_at = datetime.now(UTC)
            runner_session.last_error = str(error)
            runner_session.updated_at = datetime.now(UTC)

    @staticmethod
    def _persist_session_metrics(session_id: int, symbol: str) -> None:
        try:
            StrategyPerformanceService().persist_session_metrics(session_id, symbol)
        except Exception as exc:
            logger.exception("Failed to persist session metrics for session %s: %s", session_id, exc)

    @staticmethod
    def _record_tick_success(
        *,
        session_id: int,
        tick_number: int,
        started_at: datetime,
        finished_at: datetime,
        result,
    ) -> None:
        with session_scope() as session:
            session.add(
                RuntimeTick(
                    runner_session_id=session_id,
                    tick_number=tick_number,
                    symbol=result.strategy_decision.symbol,
                    interval=result.strategy_decision.interval,
                    strategy_action=result.strategy_decision.action,
                    final_action=result.final_action,
                    risk_approved=result.risk_approved,
                    risk_reason=result.risk_reason,
                    execution_action=result.execution_action,
                    journal_id=result.decision_id,
                    market_regime=result.market_regime,
                    candles_used=result.candles_used,
                    started_at=started_at,
                    finished_at=finished_at,
                    error=None,
                )
            )

    @staticmethod
    def _record_tick_error(
        *,
        session_id: int,
        tick_number: int,
        symbol: str,
        interval: str,
        started_at: datetime,
        error: Exception,
    ) -> None:
        with session_scope() as session:
            session.add(
                RuntimeTick(
                    runner_session_id=session_id,
                    tick_number=tick_number,
                    symbol=symbol,
                    interval=interval,
                    strategy_action="HOLD",
                    final_action="HOLD",
                    risk_approved=False,
                    risk_reason=str(error),
                    execution_action="ERROR",
                    journal_id=None,
                    market_regime=None,
                    candles_used=None,
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    error=str(error),
                )
            )

    @staticmethod
    def _get_result(session_id: int) -> RunnerStartResult:
        with session_scope() as session:
            runner_session = session.get(RunnerSession, session_id)
            assert runner_session is not None
            return RunnerStartResult(
                session_id=runner_session.id,
                status=runner_session.status,
                strategy_name=runner_session.strategy_name,
                strategy_version=runner_session.strategy_version,
                symbol=runner_session.symbol,
                interval=runner_session.interval,
                ticks_requested=runner_session.ticks_requested,
                ticks_completed=runner_session.ticks_completed,
                last_error=runner_session.last_error,
            )
