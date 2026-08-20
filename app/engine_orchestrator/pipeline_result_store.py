"""Transactional lifecycle, atomic claims, and compact result persistence."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.orchestrator_status import PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult, json_safe
from app.engine_orchestrator.trade_profile import DEFAULT_TRADE_PROFILE_ID, TradeProfileMode, resolve_trade_profile
from app.engine_orchestrator.profile_owner import ProfileOwnershipLostError
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from app.engine_paper.final_approval_materializer import (
    DEFAULT_NATURAL_FINAL_APPROVAL_MATERIALIZER,
    NaturalFinalApprovalMaterializer,
)
from app.engine_paper.shadow_approval_materializer import (
    DEFAULT_SHADOW_FINAL_APPROVAL_MATERIALIZER,
    ShadowFinalApprovalMaterializer,
)


ACTIVE_CLAIM_STATUSES = (
    PipelineStatus.PENDING.value,
    PipelineStatus.RESERVED.value,
    PipelineStatus.CHECKING_FRESHNESS.value,
    PipelineStatus.READY_TO_RUN.value,
    PipelineStatus.RUNNING.value,
)


def utc_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("orchestrator timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def persisted_utc(value: datetime) -> datetime:
    """SQLites used by isolated tests lose timezone metadata; PostgreSQL does not."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class ClaimedWindow:
    run_id: str
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    freshness_deadline_at: datetime
    freshness_attempt_count: int
    was_waiting: bool
    trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID


class PipelineResultStore:
    def __init__(self, session_or_factory: Session | Callable[[], Session], *,
                 stale_run_after_seconds: int = 300,
                 clock: Callable[[], datetime] = utc_now,
                 owner_guard: object | None = None,
                 final_approval_materializer: NaturalFinalApprovalMaterializer =
                 DEFAULT_NATURAL_FINAL_APPROVAL_MATERIALIZER,
                 shadow_approval_materializer: ShadowFinalApprovalMaterializer =
                 DEFAULT_SHADOW_FINAL_APPROVAL_MATERIALIZER) -> None:
        if stale_run_after_seconds < 1:
            raise ValueError("stale_run_after_seconds must be positive")
        self._session_or_factory = session_or_factory
        self.stale_run_after_seconds = stale_run_after_seconds
        self.clock = clock
        self.owner_guard = owner_guard
        self.final_approval_materializer = final_approval_materializer
        self.shadow_approval_materializer = shadow_approval_materializer

    @contextmanager
    def _session(self) -> Iterator[Session]:
        if isinstance(self._session_or_factory, Session):
            yield self._session_or_factory
            return
        with self._session_or_factory() as session:
            yield session

    def _now(self) -> datetime:
        return aware_utc(self.clock())

    def _require_owner(self, session: Session, trade_profile_id: str) -> None:
        profile = resolve_trade_profile(trade_profile_id)
        if profile.trade_profile_id == DEFAULT_TRADE_PROFILE_ID:
            return
        guard = self.owner_guard
        if guard is None:
            raise ProfileOwnershipLostError(
                f"profile mutation requires active owner: {profile.trade_profile_id}"
            )
        checker = getattr(guard, "assert_active", None)
        if not callable(checker):
            raise ProfileOwnershipLostError("profile owner guard is invalid")
        checker(session)

    @staticmethod
    def _deadline(row: OnlinePipelineRun) -> datetime:
        value = row.freshness_deadline_at or row.closed_until_utc
        return persisted_utc(value)

    @classmethod
    def _claim_value(cls, row: OnlinePipelineRun, *, was_waiting: bool) -> ClaimedWindow:
        return ClaimedWindow(
            run_id=row.run_id,
            trade_profile_id=row.trade_profile_id,
            symbol=row.symbol,
            primary_timeframe=row.primary_timeframe,
            closed_until_ms=int(row.closed_until_ms),
            freshness_deadline_at=cls._deadline(row),
            freshness_attempt_count=int(row.freshness_attempt_count or 0),
            was_waiting=was_waiting,
        )

    def has_window(self, symbol: str, timeframe: str, closed_until_ms: int, *,
                   trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> bool:
        query = select(OnlinePipelineRun.id).where(
            OnlinePipelineRun.trade_profile_id == resolve_trade_profile(trade_profile_id).trade_profile_id,
            OnlinePipelineRun.symbol == symbol.upper(),
            OnlinePipelineRun.primary_timeframe == timeframe,
            OnlinePipelineRun.closed_until_ms == int(closed_until_ms),
        ).limit(1)
        with self._session() as session:
            return session.scalar(query) is not None

    def reserve(self, symbol: str, timeframe: str, closed_until_ms: int, *,
                daemon_instance_id: str, trigger_source: str,
                trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID,
                freshness_deadline_at: datetime | None = None) -> str | None:
        """Register and claim a new logical window exactly once."""
        run_id = f"orchestrator:{uuid4().hex}"
        now = self._now()
        deadline = aware_utc(freshness_deadline_at) if freshness_deadline_at else utc_from_ms(closed_until_ms)
        profile = resolve_trade_profile(trade_profile_id)
        if timeframe != profile.trigger_timeframe:
            raise ValueError("reserved window timeframe/profile mismatch")
        row = OnlinePipelineRun(
            run_id=run_id, symbol=symbol.upper(), primary_timeframe=timeframe,
            trade_profile_id=profile.trade_profile_id, profile_mode=profile.mode,
            closed_until_ms=int(closed_until_ms), closed_until_utc=utc_from_ms(closed_until_ms),
            status=PipelineStatus.CHECKING_FRESHNESS.value, started_at=now,
            trigger_source=trigger_source, daemon_instance_id=daemon_instance_id,
            freshness_deadline_at=deadline, freshness_claimed_at=now,
        )
        with self._session() as session:
            self._require_owner(session, profile.trade_profile_id)
            try:
                session.add(row)
                session.commit()
                return run_id
            except IntegrityError:
                session.rollback()
                return None

    def get_claim(self, run_id: str) -> ClaimedWindow:
        with self._session() as session:
            row = session.scalar(select(OnlinePipelineRun).where(OnlinePipelineRun.run_id == run_id))
            if row is None:
                raise KeyError(f"unknown run_id {run_id}")
            return self._claim_value(row, was_waiting=bool(row.first_wait_at))

    def claim_due_waiting(self, *, daemon_instance_id: str, limit: int,
                          trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID,
                          now: datetime | None = None) -> list[ClaimedWindow]:
        """Atomically claim due waiting or stale active rows using compare-and-set."""
        if limit <= 0:
            raise ValueError("claim limit must be positive")
        claimed_at = aware_utc(now) if now else self._now()
        stale_cutoff = claimed_at - timedelta(seconds=self.stale_run_after_seconds)
        due = or_(
            and_(
                OnlinePipelineRun.status == PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value,
                OnlinePipelineRun.next_retry_at <= claimed_at,
            ),
            and_(
                OnlinePipelineRun.status.in_(ACTIVE_CLAIM_STATUSES),
                or_(
                    OnlinePipelineRun.freshness_claimed_at <= stale_cutoff,
                    and_(OnlinePipelineRun.freshness_claimed_at.is_(None),
                         or_(OnlinePipelineRun.started_at <= stale_cutoff,
                             OnlinePipelineRun.started_at.is_(None))),
                ),
            ),
        )
        profile_id = resolve_trade_profile(trade_profile_id).trade_profile_id
        query = select(OnlinePipelineRun).where(
            OnlinePipelineRun.trade_profile_id == profile_id, due
        ).order_by(
            OnlinePipelineRun.next_retry_at.asc().nulls_last(),
            OnlinePipelineRun.closed_until_ms.asc(),
        ).limit(limit * 2)
        results: list[ClaimedWindow] = []
        with self._session() as session:
            self._require_owner(session, profile_id)
            candidates = list(session.scalars(query))
            for row in candidates:
                if len(results) >= limit:
                    break
                old_status = row.status
                old_claimed_at = row.freshness_claimed_at
                conditions = [OnlinePipelineRun.id == row.id, OnlinePipelineRun.status == old_status]
                if old_status == PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value:
                    conditions.append(OnlinePipelineRun.next_retry_at <= claimed_at)
                elif old_claimed_at is None:
                    conditions.extend([
                        OnlinePipelineRun.freshness_claimed_at.is_(None),
                        or_(OnlinePipelineRun.started_at <= stale_cutoff,
                            OnlinePipelineRun.started_at.is_(None)),
                    ])
                else:
                    conditions.append(OnlinePipelineRun.freshness_claimed_at == old_claimed_at)
                    conditions.append(OnlinePipelineRun.freshness_claimed_at <= stale_cutoff)
                statement = update(OnlinePipelineRun).where(*conditions).values(
                    status=PipelineStatus.CHECKING_FRESHNESS.value,
                    daemon_instance_id=daemon_instance_id,
                    freshness_claimed_at=claimed_at,
                    started_at=claimed_at,
                    next_retry_at=None,
                ).execution_options(synchronize_session=False)
                changed = session.execute(statement)
                if changed.rowcount == 1:
                    session.commit()
                    row.status = PipelineStatus.CHECKING_FRESHNESS.value
                    row.daemon_instance_id = daemon_instance_id
                    row.freshness_claimed_at = claimed_at
                    results.append(self._claim_value(
                        row, was_waiting=old_status == PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value
                        or bool(row.first_wait_at),
                    ))
                else:
                    session.rollback()
        return results

    def mark_waiting(self, claim: ClaimedWindow, *, daemon_instance_id: str,
                     checked_at: datetime, next_retry_at: datetime,
                     reason_code: str, waiting_timeframes: tuple[str, ...],
                     payload: dict[str, Any]) -> bool:
        checked_at = aware_utc(checked_at)
        next_retry_at = aware_utc(next_retry_at)
        with self._session() as session:
            self._require_owner(session, claim.trade_profile_id)
            row = session.scalar(select(OnlinePipelineRun).where(
                OnlinePipelineRun.run_id == claim.run_id,
                OnlinePipelineRun.status == PipelineStatus.CHECKING_FRESHNESS.value,
                OnlinePipelineRun.daemon_instance_id == daemon_instance_id,
            ))
            if row is None:
                return False
            row.status = PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value
            row.freshness_attempt_count = int(row.freshness_attempt_count or 0) + 1
            row.first_freshness_checked_at = row.first_freshness_checked_at or checked_at
            row.last_freshness_checked_at = checked_at
            row.first_wait_at = row.first_wait_at or checked_at
            row.next_retry_at = next_retry_at
            row.freshness_claimed_at = None
            row.waiting_reason_code = reason_code
            row.waiting_timeframes = list(waiting_timeframes)
            row.last_freshness_payload = json_safe(payload)
            row.market_data_freshness_status = str(payload.get("status") or reason_code)
            session.commit()
            return True

    def mark_running(self, claim: ClaimedWindow, *, daemon_instance_id: str,
                     checked_at: datetime, payload: dict[str, Any]) -> bool:
        checked_at = aware_utc(checked_at)
        with self._session() as session:
            self._require_owner(session, claim.trade_profile_id)
            row = session.scalar(select(OnlinePipelineRun).where(
                OnlinePipelineRun.run_id == claim.run_id,
                OnlinePipelineRun.status == PipelineStatus.CHECKING_FRESHNESS.value,
                OnlinePipelineRun.daemon_instance_id == daemon_instance_id,
            ))
            if row is None:
                return False
            row.status = PipelineStatus.RUNNING.value
            row.freshness_attempt_count = int(row.freshness_attempt_count or 0) + 1
            row.first_freshness_checked_at = row.first_freshness_checked_at or checked_at
            row.last_freshness_checked_at = checked_at
            row.next_retry_at = None
            row.waiting_reason_code = None
            row.waiting_timeframes = None
            row.last_freshness_payload = json_safe(payload)
            row.market_data_freshness_status = "READY"
            if row.first_wait_at is not None and row.freshness_recovered_at is None:
                row.freshness_recovered_at = checked_at
            session.commit()
            return True

    def mark_terminal_freshness(self, claim: ClaimedWindow, *, daemon_instance_id: str,
                                checked_at: datetime, status: str, reason_code: str,
                                waiting_timeframes: tuple[str, ...],
                                payload: dict[str, Any]) -> bool:
        checked_at = aware_utc(checked_at)
        with self._session() as session:
            self._require_owner(session, claim.trade_profile_id)
            row = session.scalar(select(OnlinePipelineRun).where(
                OnlinePipelineRun.run_id == claim.run_id,
                OnlinePipelineRun.status == PipelineStatus.CHECKING_FRESHNESS.value,
                OnlinePipelineRun.daemon_instance_id == daemon_instance_id,
            ))
            if row is None:
                return False
            row.status = status
            row.freshness_attempt_count = int(row.freshness_attempt_count or 0) + 1
            row.first_freshness_checked_at = row.first_freshness_checked_at or checked_at
            row.last_freshness_checked_at = checked_at
            row.finished_at = checked_at
            row.next_retry_at = None
            row.waiting_reason_code = reason_code
            row.waiting_timeframes = list(waiting_timeframes)
            row.last_freshness_payload = json_safe(payload)
            row.market_data_freshness_status = reason_code
            row.final_result = "NO_ACTION"
            row.final_reason = reason_code
            session.commit()
            return True

    def finish(self, run_id: str, result: PipelineResult, *, freshness_status: str) -> bool:
        now = self._now()
        with self._session() as session:
            run = session.scalar(select(OnlinePipelineRun).where(OnlinePipelineRun.run_id == run_id))
            if run is None:
                raise KeyError(f"unknown run_id {run_id}")
            self._require_owner(session, run.trade_profile_id)
            if result.trade_profile_id != run.trade_profile_id:
                raise ValueError("result/run trade-profile identity mismatch")
            if run.trade_profile_id != DEFAULT_TRADE_PROFILE_ID and (
                result.runtime_parameter_set_id
                != resolve_runtime_parameters(run.trade_profile_id).parameter_set_id
            ):
                raise ValueError("runtime parameter identity changed or is missing")
            if session.scalar(select(OnlinePipelineResultRow.id).where(
                    OnlinePipelineResultRow.run_id == run_id)) is not None:
                return False
            if run.status not in {PipelineStatus.RUNNING.value}:
                return False
            run.status = result.status
            run.finished_at = now
            started = persisted_utc(run.started_at or now)
            run.duration_ms = max(0, int((now - started).total_seconds() * 1000))
            run.market_data_freshness_status = freshness_status
            run.analysis_status = result.analysis_status
            run.setup_status = result.setup_status
            run.strategy_status = result.strategy_status
            run.risk_status = result.risk_status
            run.paper_status = result.paper_status
            run.final_result = result.final_result
            run.final_reason = result.final_reason
            run.error_code = result.error_code
            run.error_message = result.error_message
            counters = result.safety_counters
            run.future_bars_used = counters.future_bars_used_count > 0
            run.is_trade_signal = counters.trade_signal_count > 0
            run.is_executable = counters.is_executable_count > 0
            run.order_approved = counters.order_approved_count > 0
            run.execution_approved = counters.execution_approved_count > 0
            run.position_opened = counters.position_opened_count > 0
            run.position_size_approved = counters.position_size_approved_count > 0
            if run.trade_profile_id == DEFAULT_TRADE_PROFILE_ID:
                materialized = self.final_approval_materializer.materialize(
                    session, run_id=run_id, result=result, evaluation_time=now
                )
                persisted_paper_payload = materialized.paper_payload
                final_approval_created = materialized.final_approval_created
            else:
                if run.profile_mode != TradeProfileMode.SHADOW_SEARCH.value:
                    raise ValueError("non-default profile must remain SHADOW_SEARCH")
                materialized = self.shadow_approval_materializer.materialize(
                    session, run_id=run_id, result=result, evaluation_time=now
                )
                persisted_paper_payload = materialized.paper_payload
                final_approval_created = False
            if final_approval_created:
                run.is_trade_signal = True
                run.is_executable = True
                run.order_approved = True
                run.execution_approved = True
                run.position_size_approved = True
            session.add(OnlinePipelineResultRow(
                run_id=run_id, symbol=result.symbol, primary_timeframe=result.primary_timeframe,
                trade_profile_id=result.trade_profile_id, profile_mode=result.profile_mode,
                closed_until_ms=result.closed_until_ms,
                market_data_payload_json=json_safe(result.market_data_payload),
                analysis_payload_json=json_safe(result.analysis_payload),
                setup_payload_json=json_safe(result.setup_payload),
                strategy_payload_json=json_safe(result.strategy_payload),
                risk_payload_json=json_safe(result.risk_payload),
                paper_payload_json=json_safe(persisted_paper_payload),
                module_reasons_json=json_safe(result.module_reasons),
                module_warnings_json=json_safe(result.module_warnings),
                safety_counters_json=json_safe(result.safety_counters),
            ))
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    def get_latest(self, symbol: str, timeframe: str, *,
                   trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> OnlinePipelineRun | None:
        query = select(OnlinePipelineRun).where(
            OnlinePipelineRun.trade_profile_id == resolve_trade_profile(trade_profile_id).trade_profile_id,
            OnlinePipelineRun.symbol == symbol.upper(),
            OnlinePipelineRun.primary_timeframe == timeframe,
        ).order_by(OnlinePipelineRun.closed_until_ms.desc()).limit(1)
        with self._session() as session:
            return session.scalar(query)

    def count(self, symbol: str | None = None, *,
              trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> int:
        query = select(OnlinePipelineRun).where(
            OnlinePipelineRun.trade_profile_id == resolve_trade_profile(trade_profile_id).trade_profile_id
        )
        if symbol is not None:
            query = query.where(OnlinePipelineRun.symbol == symbol.upper())
        with self._session() as session:
            return len(list(session.scalars(query)))

    def waiting_metrics(self, *, now: datetime | None = None,
                        trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> dict[str, Any]:
        observed_at = aware_utc(now) if now else self._now()
        profile_id = resolve_trade_profile(trade_profile_id).trade_profile_id
        with self._session() as session:
            waiting = list(session.scalars(select(OnlinePipelineRun).where(
                OnlinePipelineRun.trade_profile_id == profile_id,
                OnlinePipelineRun.status == PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value
            )))
            all_rows = list(session.scalars(select(OnlinePipelineRun).where(
                OnlinePipelineRun.trade_profile_id == profile_id
            )))
        by_timeframe: dict[str, int] = {}
        by_symbol: dict[str, int] = {}
        for row in waiting:
            by_symbol[row.symbol] = by_symbol.get(row.symbol, 0) + 1
            for timeframe in row.waiting_timeframes or []:
                by_timeframe[timeframe] = by_timeframe.get(timeframe, 0) + 1
        first_waits = [persisted_utc(row.first_wait_at) for row in waiting if row.first_wait_at]
        next_retries = [persisted_utc(row.next_retry_at) for row in waiting if row.next_retry_at]
        recovered = [row for row in all_rows if row.freshness_recovered_at is not None]
        timeouts = [
            row for row in all_rows
            if row.status == PipelineStatus.SKIPPED_FRESHNESS_TIMEOUT.value
            or (
                row.status == PipelineStatus.SKIPPED_FRESHNESS_NOT_OK.value
                and row.final_reason == "FRESHNESS_DEADLINE_EXCEEDED"
            )
        ]
        retry_total = sum(max(0, int(row.freshness_attempt_count or 0) - 1) for row in all_rows)
        return {
            "waiting_windows": len(waiting),
            "waiting_by_timeframe": by_timeframe,
            "waiting_by_symbol": by_symbol,
            "oldest_wait_age_seconds": max((observed_at - min(first_waits)).total_seconds(), 0) if first_waits else 0,
            "next_retry_at": min(next_retries).isoformat().replace("+00:00", "Z") if next_retries else None,
            "freshness_retry_attempts_total": retry_total,
            "freshness_recovered_total": len(recovered),
            "freshness_timeouts_total": len(timeouts),
            "last_freshness_recovery_at": max((persisted_utc(row.freshness_recovered_at) for row in recovered), default=None),
            "last_freshness_timeout_at": max((persisted_utc(row.finished_at) for row in timeouts if row.finished_at), default=None),
        }

    def safety_totals(self, *, trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID) -> dict[str, int]:
        totals: dict[str, int] = {}
        with self._session() as session:
            payloads = list(session.scalars(select(OnlinePipelineResultRow.safety_counters_json).where(
                OnlinePipelineResultRow.trade_profile_id == resolve_trade_profile(trade_profile_id).trade_profile_id
            )))
        for payload in payloads:
            for name, value in dict(payload or {}).items():
                totals[name] = totals.get(name, 0) + int(value or 0)
        return totals
