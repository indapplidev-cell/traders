"""Durable, exact correlation for the bounded first PAPER canary.

This module owns identity and lifecycle evidence only.  It does not decide a
trade, calculate PnL, enable a runtime, or call an exchange.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperFirstCanarySessionRecord,
    PaperPositionRecord,
)
from app.engine_paper.eligible_approval_ranking import (
    DEFAULT_NEW_CANARY_SELECTION_POLICY_VERSION,
    LEGACY_EXACTLY_ONE_POLICY_VERSION,
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
)


TERMINAL_CANARY_STATES = frozenset({"COMPLETED", "STOPPED", "FAILED_SAFE"})


def continuous_cycle_id(generation: int, candidate_identity: str) -> str:
    """Return the stable cycle id used to recover a partially dispatched candidate."""

    return str(uuid5(NAMESPACE_URL, f"traders:paper:continuous:{generation}:{candidate_identity}"))


class PaperFirstCanaryState(StrEnum):
    RESERVED = "RESERVED"
    ARMED = "ARMED"
    ARMED_WAITING = "ARMED_WAITING"
    NO_ELIGIBLE_APPROVAL = "NO_ELIGIBLE_APPROVAL"
    RUNNING = "RUNNING"
    POSITION_OPEN = "POSITION_OPEN"
    POSITION_CLOSING = "POSITION_CLOSING"
    POSITION_CLOSED = "POSITION_CLOSED"
    RECONCILIATION_PENDING = "RECONCILIATION_PENDING"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    FAILED_SAFE = "FAILED_SAFE"


class CanaryCorrelationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class PaperFirstCanarySession:
    canary_id: str
    environment: str
    mode: str
    state: PaperFirstCanaryState
    created_at: datetime
    armed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    arm_request_id: str
    arming_transition_id: str | None
    arming_generation: int | None
    start_request_id: str | None
    current_control_generation: int
    max_new_commands: int
    max_open_positions: int
    allowed_symbols: tuple[str, ...]
    approval_id: str | None
    command_count: int
    command_id: str | None
    position_count: int
    position_id: str | None
    trade_report_available: bool
    paper_reconciliation_status: str
    accounting_reconciliation_status: str
    reconciliation_checked_at: datetime | None
    terminal_reason: str | None
    finding_codes: tuple[str, ...]
    version: int
    selection_policy_version: str = LEGACY_EXACTLY_ONE_POLICY_VERSION
    universe_version_id: str = "trading-universe-v1"
    authority_mode: str = "FIRST_CANARY_HISTORICAL"
    continuous_cycle_number: int | None = None

def _snapshot(row: PaperFirstCanarySessionRecord) -> PaperFirstCanarySession:
    try:
        UUID(row.canary_id)
        state = PaperFirstCanaryState(row.state)
        symbols = tuple(row.allowed_symbols)
        findings = tuple(row.finding_codes)
    except (TypeError, ValueError) as exc:
        raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE") from exc
    if (
        len(symbols) == 0
        or len(set(symbols)) != len(symbols)
        or row.command_count not in (0, 1)
        or row.position_count not in (0, 1)
        or (row.command_count == 1) != (row.command_id is not None)
        or (row.position_count == 1) != (row.position_id is not None)
        or row.version < 0
        or row.selection_policy_version not in {
            LEGACY_EXACTLY_ONE_POLICY_VERSION,
            MULTI_SYMBOL_SELECTION_POLICY_VERSION,
        }
        or row.universe_version_id not in {"trading-universe-v1", "trading-universe-v2"}
    ):
        raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE")
    return PaperFirstCanarySession(
        canary_id=row.canary_id,
        environment=row.environment,
        mode=row.mode,
        state=state,
        created_at=row.created_at,
        armed_at=row.armed_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
        arm_request_id=row.arm_request_id,
        arming_transition_id=row.arming_transition_id,
        arming_generation=row.arming_generation,
        start_request_id=row.start_request_id,
        current_control_generation=row.current_control_generation,
        max_new_commands=row.max_new_commands,
        max_open_positions=row.max_open_positions,
        allowed_symbols=symbols,
        approval_id=row.approval_id,
        command_count=row.command_count,
        command_id=row.command_id,
        position_count=row.position_count,
        position_id=row.position_id,
        trade_report_available=row.trade_report_available,
        paper_reconciliation_status=row.paper_reconciliation_status,
        accounting_reconciliation_status=row.accounting_reconciliation_status,
        reconciliation_checked_at=row.reconciliation_checked_at,
        terminal_reason=row.terminal_reason,
        finding_codes=findings,
        version=row.version,
        selection_policy_version=row.selection_policy_version,
        universe_version_id=row.universe_version_id,
        authority_mode=row.authority_mode,
        continuous_cycle_number=row.continuous_cycle_number,
    )


class PaperFirstCanaryRepository:
    """Transaction-bound exact-PK repository; methods flush but never commit."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _validated(self, row: PaperFirstCanarySessionRecord) -> PaperFirstCanarySession:
        value = _snapshot(row)
        if value.command_id is not None:
            command = self.session.get(PaperExecutionCommandRecord, value.command_id)
            if command is None or command.symbol not in value.allowed_symbols:
                raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE")
        if value.position_id is not None:
            position = self.session.get(PaperPositionRecord, value.position_id)
            if position is None or position.symbol not in value.allowed_symbols:
                raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE")
        return value

    def get(self, canary_id: str, *, for_update: bool = False) -> PaperFirstCanarySession | None:
        query = select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).limit(1)
        if for_update:
            query = query.with_for_update()
        row = self.session.scalar(query)
        return self._validated(row) if row is not None else None

    def get_by_arm_request(self, request_id: str, *, for_update: bool = False) -> PaperFirstCanarySession | None:
        query = select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.arm_request_id == request_id
        ).limit(1)
        if for_update:
            query = query.with_for_update()
        row = self.session.scalar(query)
        return self._validated(row) if row is not None else None

    def get_by_position(self, position_id: str) -> PaperFirstCanarySession | None:
        row = self.session.scalar(
            select(PaperFirstCanarySessionRecord)
            .where(PaperFirstCanarySessionRecord.position_id == position_id)
            .order_by(
                PaperFirstCanarySessionRecord.created_at.desc(),
                PaperFirstCanarySessionRecord.canary_id.desc(),
            )
            .limit(1)
        )
        return self._validated(row) if row is not None else None

    def current(self) -> PaperFirstCanarySession | None:
        rows = tuple(self.session.scalars(
            select(PaperFirstCanarySessionRecord)
            .where(PaperFirstCanarySessionRecord.state.not_in(tuple(TERMINAL_CANARY_STATES)))
            .order_by(PaperFirstCanarySessionRecord.created_at, PaperFirstCanarySessionRecord.canary_id)
            .limit(2)
        ))
        if len(rows) > 1:
            raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE")
        return self._validated(rows[0]) if rows else None

    def supervised(self) -> PaperFirstCanarySession | None:
        """Return the active session or rehydrate its persisted open position."""

        current = self.current()
        if current is not None:
            return current
        rows = tuple(self.session.scalars(
            select(PaperFirstCanarySessionRecord)
            .join(
                PaperPositionRecord,
                PaperPositionRecord.position_id
                == PaperFirstCanarySessionRecord.position_id,
            )
            .where(PaperPositionRecord.state.in_(("OPEN", "CLOSING")))
            .order_by(
                PaperFirstCanarySessionRecord.created_at,
                PaperFirstCanarySessionRecord.canary_id,
            )
            .limit(2)
        ))
        if len(rows) > 1:
            raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE")
        return self._validated(rows[0]) if rows else None

    def reserve_arm(
        self,
        *,
        request_id: str,
        fingerprint: str,
        expected_generation: int,
        allowed_symbols: tuple[str, ...],
        now: datetime,
        selection_policy_version: str = DEFAULT_NEW_CANARY_SELECTION_POLICY_VERSION,
        universe_version_id: str = "trading-universe-v1",
    ) -> PaperFirstCanarySession:
        replay = self.get_by_arm_request(request_id, for_update=True)
        if replay is not None:
            row = self.session.get(PaperFirstCanarySessionRecord, replay.canary_id)
            assert row is not None
            if row.arm_request_fingerprint != fingerprint:
                raise CanaryCorrelationError("REQUEST_ID_CONFLICT")
            return replay
        active = self.current()
        if active is not None:
            raise CanaryCorrelationError("CANARY_ALREADY_ACTIVE")
        row = PaperFirstCanarySessionRecord(
            canary_id=str(uuid4()), environment="PRODUCTION", mode="PAPER", state="RESERVED",
            created_at=now, armed_at=None, started_at=None, completed_at=None,
            arm_request_id=request_id, arm_request_fingerprint=fingerprint,
            arming_transition_id=None, arming_generation=None, start_request_id=None,
            start_request_fingerprint=None, current_control_generation=expected_generation,
            max_new_commands=1, max_open_positions=1, allowed_symbols=list(allowed_symbols),
            universe_version_id=universe_version_id,
            selection_policy_version=selection_policy_version,
            approval_id=None, command_count=0, command_id=None, position_count=0,
            position_id=None, trade_report_available=False, paper_reconciliation_status="NOT_STARTED",
            accounting_reconciliation_status="NOT_STARTED", reconciliation_checked_at=None,
            terminal_reason=None, finding_codes=[], version=0,
            authority_mode="FIRST_CANARY_HISTORICAL", continuous_cycle_number=None,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise CanaryCorrelationError("CANARY_ALREADY_ACTIVE") from exc
        return _snapshot(row)

    def complete_arm(self, canary_id: str, transition_id: str, generation: int, now: datetime) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        if row.state == "ARMED":
            if (row.arming_transition_id, row.arming_generation) != (transition_id, generation):
                raise CanaryCorrelationError("CANARY_CORRELATION_CONFLICT")
            return _snapshot(row)
        if row.state != "RESERVED":
            raise CanaryCorrelationError("CANARY_CORRELATION_CONFLICT")
        row.state = "ARMED"
        row.arming_transition_id = transition_id
        row.arming_generation = generation
        row.current_control_generation = generation
        row.armed_at = now
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def reserve_start(self, canary_id: str, request_id: str, fingerprint: str, transition_id: str, generation: int) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        if row.arming_transition_id != transition_id or row.arming_generation != generation:
            raise CanaryCorrelationError("CANARY_NOT_ARMED")
        if row.start_request_id is not None:
            if row.start_request_id != request_id or row.start_request_fingerprint != fingerprint:
                raise CanaryCorrelationError("CANARY_ALREADY_STARTED")
            return _snapshot(row)
        if row.state != "ARMED":
            raise CanaryCorrelationError("CANARY_NOT_ARMED")
        row.start_request_id = request_id
        row.start_request_fingerprint = fingerprint
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def mark_started(self, canary_id: str, *, no_approval: bool, now: datetime) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        target = "NO_ELIGIBLE_APPROVAL" if no_approval else "RUNNING"
        if row.state in (target, "RUNNING", "POSITION_OPEN", "POSITION_CLOSING", "POSITION_CLOSED", "RECONCILIATION_PENDING", "COMPLETED"):
            # Recover an uncertain outcome where the executor committed the
            # command graph (which advances the canary) before the control
            # service durably recorded START completion.
            if row.start_request_id is not None and row.started_at is None:
                row.started_at = now
                row.version += 1
                self.session.flush()
            return _snapshot(row)
        if row.state != "ARMED" or row.start_request_id is None:
            raise CanaryCorrelationError("CANARY_CORRELATION_CONFLICT")
        row.state = target
        row.started_at = now
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def fail_safe(self, canary_id: str, code: str, now: datetime | None = None) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        row.state = "FAILED_SAFE"
        row.terminal_reason = code
        row.finding_codes = list(dict.fromkeys([*row.finding_codes, code]))
        row.completed_at = now or datetime.now(timezone.utc)
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def reserve_continuous_cycle(
        self,
        *,
        candidate_identity: str,
        generation: int,
        control_transition_id: str,
        allowed_symbols: tuple[str, ...],
        now: datetime,
    ) -> PaperFirstCanarySession:
        """Create or recover one v2-only execution cycle under continuous authority."""

        active = self.current()
        deterministic_id = continuous_cycle_id(generation, candidate_identity)
        if active is not None:
            if active.canary_id == deterministic_id and active.authority_mode == "CONTINUOUS":
                return active
            raise CanaryCorrelationError("CONTINUOUS_CYCLE_ALREADY_ACTIVE")
        existing = self.get(deterministic_id, for_update=True)
        if existing is not None:
            return existing
        cycle_number = int(self.session.scalar(
            select(func.coalesce(func.max(PaperFirstCanarySessionRecord.continuous_cycle_number), 0))
        ) or 0) + 1
        request_identity = f"continuous:{generation}:{candidate_identity}"[:128]
        row = PaperFirstCanarySessionRecord(
            canary_id=deterministic_id, environment="PRODUCTION", mode="PAPER", state="ARMED",
            created_at=now, armed_at=now, started_at=now, completed_at=None,
            arm_request_id=request_identity,
            arm_request_fingerprint=f"continuous:{candidate_identity}"[:64],
            arming_transition_id=str(uuid5(NAMESPACE_URL, f"{control_transition_id}:{candidate_identity}")),
            arming_generation=generation, start_request_id=request_identity,
            start_request_fingerprint=f"continuous:{candidate_identity}"[:64],
            current_control_generation=generation,
            max_new_commands=1, max_open_positions=1, allowed_symbols=list(allowed_symbols),
            universe_version_id="trading-universe-v2",
            selection_policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION,
            approval_id=None, command_count=0, command_id=None, position_count=0,
            position_id=None, trade_report_available=False,
            paper_reconciliation_status="NOT_STARTED",
            accounting_reconciliation_status="NOT_STARTED", reconciliation_checked_at=None,
            terminal_reason=None, finding_codes=[], version=0,
            authority_mode="CONTINUOUS", continuous_cycle_number=cycle_number,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError as exc:
            recovered = self.get(deterministic_id, for_update=True)
            if recovered is not None:
                return recovered
            raise CanaryCorrelationError("CONTINUOUS_CYCLE_ALREADY_ACTIVE") from exc
        return _snapshot(row)

    def stop_waiting(
        self,
        canary_id: str,
        *,
        control_generation: int,
        reason: str,
        now: datetime | None = None,
    ) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        if row.state == "STOPPED":
            return _snapshot(row)
        if (
            row.state != "NO_ELIGIBLE_APPROVAL"
            or row.command_count != 0 or row.command_id is not None
            or row.position_count != 0 or row.position_id is not None
            or row.approval_id is not None
        ):
            raise CanaryCorrelationError("CANARY_NOT_SAFE_TO_STOP")
        row.state = "STOPPED"
        row.current_control_generation = control_generation
        row.completed_at = now or datetime.now(timezone.utc)
        row.terminal_reason = reason
        row.finding_codes = []
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def link_command(self, canary_id: str, command_id: str, symbol: str) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        authority = "CONTINUOUS" if row.authority_mode == "CONTINUOUS" else "FIRST_CANARY"
        if symbol not in row.allowed_symbols:
            return self.fail_safe(canary_id, f"{authority}_SYMBOL_SCOPE_VIOLATION")
        if row.command_id == command_id and row.command_count == 1:
            return _snapshot(row)
        if row.command_id is not None or row.command_count != 0:
            return self.fail_safe(canary_id, f"{authority}_COMMAND_BUDGET_VIOLATION")
        command = self.session.get(PaperExecutionCommandRecord, command_id)
        if command is None or not command.risk_decision_id:
            return self.fail_safe(canary_id, "CANARY_CORRELATION_UNAVAILABLE")
        if row.approval_id is not None and row.approval_id != command.risk_decision_id:
            return self.fail_safe(canary_id, "CANARY_APPROVAL_CONSUMPTION_CONFLICT")
        row.approval_id = command.risk_decision_id
        row.command_id = command_id
        row.command_count = 1
        row.state = "RUNNING"
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def link_position_for_command(self, command_id: str, position_id: str, symbol: str) -> PaperFirstCanarySession | None:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.command_id == command_id
        ).with_for_update())
        if row is None:
            return None
        authority = "CONTINUOUS" if row.authority_mode == "CONTINUOUS" else "FIRST_CANARY"
        if symbol not in row.allowed_symbols:
            return self.fail_safe(row.canary_id, f"{authority}_SYMBOL_SCOPE_VIOLATION")
        if row.position_id == position_id and row.position_count == 1:
            return _snapshot(row)
        if row.position_id is not None or row.position_count != 0:
            return self.fail_safe(row.canary_id, f"{authority}_POSITION_BUDGET_VIOLATION")
        row.position_id = position_id
        row.position_count = 1
        row.state = "POSITION_OPEN"
        row.version += 1
        self.session.flush()
        return _snapshot(row)

    def refresh_terminal(
        self,
        canary_id: str,
        *,
        control_state: str,
        control_generation: int,
        report_available: bool,
        paper_reconciliation_status: str,
        accounting_reconciliation_status: str,
        checked_at: datetime,
    ) -> PaperFirstCanarySession:
        row = self.session.scalar(select(PaperFirstCanarySessionRecord).where(
            PaperFirstCanarySessionRecord.canary_id == canary_id
        ).with_for_update())
        if row is None:
            raise CanaryCorrelationError("CANARY_NOT_FOUND")
        row.current_control_generation = control_generation
        row.paper_reconciliation_status = paper_reconciliation_status
        row.accounting_reconciliation_status = accounting_reconciliation_status
        row.reconciliation_checked_at = checked_at
        row.trade_report_available = report_available
        if row.position_id is not None:
            position = self.session.get(PaperPositionRecord, row.position_id)
            if position is None:
                return self.fail_safe(canary_id, "CANARY_CORRELATION_UNAVAILABLE", checked_at)
            if position.symbol not in row.allowed_symbols:
                authority = "CONTINUOUS" if row.authority_mode == "CONTINUOUS" else "FIRST_CANARY"
                return self.fail_safe(canary_id, f"{authority}_SYMBOL_SCOPE_VIOLATION", checked_at)
            if position.state == "OPEN":
                row.state = "POSITION_OPEN"
            elif position.state == "CLOSING":
                row.state = "POSITION_CLOSING"
            elif position.state == "CLOSED":
                row.state = "POSITION_CLOSED"
                healthy = paper_reconciliation_status == "HEALTHY" and accounting_reconciliation_status == "HEALTHY"
                expected_control = (
                    "CONTINUOUS_ARMED" if row.authority_mode == "CONTINUOUS" else "DISABLED"
                )
                if not report_available or not healthy or control_state != expected_control:
                    row.state = "RECONCILIATION_PENDING"
                    row.finding_codes = ["CANARY_RECONCILIATION_PENDING"]
                else:
                    row.state = "COMPLETED"
                    row.completed_at = checked_at
                    row.finding_codes = []
        row.version += 1
        self.session.flush()
        return _snapshot(row)


class SqlAlchemyPaperFirstCanaryStore:
    """Short-transaction service used by the control API and recovery lookups."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _write(self, operation):
        with self._session_factory() as session:
            try:
                value = operation(PaperFirstCanaryRepository(session))
                session.commit()
                return value
            except CanaryCorrelationError:
                session.rollback()
                raise
            except (IntegrityError, SQLAlchemyError) as exc:
                session.rollback()
                raise CanaryCorrelationError("CANARY_CORRELATION_UNAVAILABLE") from exc

    def reserve_arm(self, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.reserve_arm(**kwargs))

    def complete_arm(self, *args, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.complete_arm(*args, **kwargs))

    def reserve_start(self, *args, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.reserve_start(*args, **kwargs))

    def mark_started(self, *args, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.mark_started(*args, **kwargs))

    def fail_safe(self, *args, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.fail_safe(*args, **kwargs))

    def stop_waiting(self, *args, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.stop_waiting(*args, **kwargs))

    def get(self, canary_id: str) -> PaperFirstCanarySession | None:
        with self._session_factory() as session:
            return PaperFirstCanaryRepository(session).get(canary_id)

    def current(self) -> PaperFirstCanarySession | None:
        with self._session_factory() as session:
            return PaperFirstCanaryRepository(session).current()

    def supervised(self) -> PaperFirstCanarySession | None:
        with self._session_factory() as session:
            return PaperFirstCanaryRepository(session).supervised()

    def get_by_arm_request(self, request_id: str) -> PaperFirstCanarySession | None:
        with self._session_factory() as session:
            return PaperFirstCanaryRepository(session).get_by_arm_request(request_id)

    def get_by_position(self, position_id: str) -> PaperFirstCanarySession | None:
        with self._session_factory() as session:
            return PaperFirstCanaryRepository(session).get_by_position(position_id)

    def refresh_terminal(self, *args, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.refresh_terminal(*args, **kwargs))

    def reserve_continuous_cycle(self, **kwargs) -> PaperFirstCanarySession:
        return self._write(lambda repo: repo.reserve_continuous_cycle(**kwargs))


__all__ = (
    "CanaryCorrelationError",
    "continuous_cycle_id",
    "PaperFirstCanaryRepository",
    "PaperFirstCanarySession",
    "PaperFirstCanaryState",
    "SqlAlchemyPaperFirstCanaryStore",
    "TERMINAL_CANARY_STATES",
)
