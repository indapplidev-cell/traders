"""Transactional PAPER repositories.

Lock order is command -> order -> position -> exit decision, followed only by
fill/event/journal inserts. Methods flush but never commit; PaperUnitOfWork is
the sole outer transaction owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.paper_mappings import (
    orm_values_to_paper_command,
    orm_values_to_paper_event,
    orm_values_to_paper_exit_decision,
    orm_values_to_paper_fill,
    orm_values_to_paper_order,
    orm_values_to_paper_position,
    paper_command_to_orm_values,
    paper_event_to_journal_values,
    paper_exit_decision_to_orm_values,
    paper_fill_to_orm_values,
    paper_order_to_orm_values,
    paper_position_to_orm_values,
)
from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_execution.paper_idempotency import journal_event_idempotency_key
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_execution.paper_state_machine import (
    command_created_event,
    fill_order,
    transition_order,
)
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_paper.db_failures import classify_database_failure
from app.engine_paper.repository_results import RepositoryOutcome, RepositoryResult, result
from app.engine_paper.semantic_idempotency import (
    command_semantic_tuple,
    exit_semantic_tuple,
    fill_semantic_tuple,
    journal_semantic_tuple,
    order_semantic_tuple,
)
from app.engine_position.paper_models import PaperPosition
from app.engine_position.paper_state_machine import (
    apply_close_fill,
    apply_entry_fill,
    begin_closing,
    fail_position as domain_fail_position,
)
from app.engine_safety.paper_domain import (
    PaperDomainError,
    PaperEventType,
    PaperOrderState,
    PaperPositionState,
    PaperReasonCode,
)


MAX_GRAPH_ROWS = 100
MAX_JOURNAL_ROWS = 200
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PaperCommandGraph:
    command: PaperExecutionCommand
    orders: tuple[PaperOrder, ...]
    fills: tuple[PaperFill, ...]
    positions: tuple[PaperPosition, ...]
    exit_decisions: tuple[PaperExitDecision, ...]
    journal: tuple[PaperDomainEvent, ...]


@dataclass(frozen=True, slots=True)
class EntryFillGraph:
    order: PaperOrder
    fill: PaperFill
    position: PaperPosition


@dataclass(frozen=True, slots=True)
class CloseFillGraph:
    order: PaperOrder
    fill: PaperFill
    position: PaperPosition


def _same(existing: T, proposed: T, semantic) -> RepositoryResult[T]:
    if semantic(existing) == semantic(proposed):
        return result(RepositoryOutcome.EXISTING_IDEMPOTENT, existing)
    return result(
        RepositoryOutcome.IDEMPOTENCY_CONFLICT,
        existing,
        reason_code="PAPER_IDEMPOTENCY_IDENTITY_COLLISION",
    )


def _domain_failure(exception: PaperDomainError) -> RepositoryResult:
    code = exception.reason_code.value
    if "VERSION" in code:
        outcome = RepositoryOutcome.STALE_VERSION
    else:
        outcome = RepositoryOutcome.INVALID_STATE
    return result(outcome, reason_code=code, message="domain transition rejected")


def _journal_values(event: PaperDomainEvent, **links: str | None) -> dict[str, object]:
    values = paper_event_to_journal_values(event, **links)
    values["idempotency_key"] = journal_event_idempotency_key(
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        causation_id=event.causation_id,
        event_type=event.event_type,
    )
    return values


def _order_event_values(
    event: PaperDomainEvent,
    *,
    previous_state: PaperOrderState | None,
    state: PaperOrderState,
) -> dict[str, object]:
    return {
        "order_event_id": event.event_id,
        "order_id": event.aggregate_id,
        "event_type": event.event_type.value,
        "from_state": previous_state.value if previous_state else None,
        "to_state": state.value,
        "aggregate_version": event.aggregate_version,
        "idempotency_key": journal_event_idempotency_key(
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            causation_id=event.causation_id,
            event_type=event.event_type,
        ),
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
        "reason_code": event.reason_code.value,
        "occurred_at": event.occurred_at,
    }


class CommandRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_command(self, command_id: str) -> PaperExecutionCommand | None:
        row = self.session.get(PaperExecutionCommandRecord, command_id)
        return orm_values_to_paper_command(row) if row else None

    def get_command_by_idempotency_key(self, key: str) -> PaperExecutionCommand | None:
        row = self.session.scalar(
            select(PaperExecutionCommandRecord).where(
                PaperExecutionCommandRecord.idempotency_key == key
            ).limit(1)
        )
        return orm_values_to_paper_command(row) if row else None

    def create_or_get_command(
        self, command: PaperExecutionCommand
    ) -> RepositoryResult[PaperExecutionCommand]:
        existing = self.get_command_by_idempotency_key(command.idempotency_key)
        if existing:
            return _same(existing, command, command_semantic_tuple)
        event = command_created_event(
            command,
            occurred_at=command.created_at,
            event_id=journal_event_idempotency_key(
                aggregate_type="paper_command",
                aggregate_id=command.command_id,
                causation_id=command.analysis_result_id,
                event_type=PaperEventType.PAPER_COMMAND_CREATED,
            ),
        )
        try:
            with self.session.begin_nested():
                self.session.add(PaperExecutionCommandRecord(**paper_command_to_orm_values(command)))
                self.session.add(
                    PaperJournalEntryRecord(
                        **_journal_values(event, command_id=command.command_id)
                    )
                )
                self.session.flush()
        except IntegrityError as exception:
            existing = self.get_command_by_idempotency_key(command.idempotency_key)
            if existing:
                return _same(existing, command, command_semantic_tuple)
            failure = classify_database_failure(exception)
            return result(failure.outcome, reason_code=failure.reason_code)
        return result(RepositoryOutcome.CREATED, command)

    def get_command_graph(
        self, command_id: str, *, limit: int = MAX_GRAPH_ROWS
    ) -> RepositoryResult[PaperCommandGraph]:
        if limit < 1 or limit > MAX_GRAPH_ROWS:
            return result(
                RepositoryOutcome.CONSTRAINT_VIOLATION,
                reason_code="PAPER_REPOSITORY_LIMIT_INVALID",
            )
        command = self.get_command(command_id)
        if not command:
            return result(RepositoryOutcome.NOT_FOUND)
        order_rows = tuple(
            self.session.scalars(
                select(PaperOrderRecord)
                .where(PaperOrderRecord.command_id == command_id)
                .order_by(PaperOrderRecord.created_at, PaperOrderRecord.order_id)
                .limit(limit)
            )
        )
        order_ids = [row.order_id for row in order_rows]
        fill_rows = tuple(
            self.session.scalars(
                select(PaperFillRecord)
                .where(PaperFillRecord.order_id.in_(order_ids or [""]))
                .order_by(PaperFillRecord.filled_at, PaperFillRecord.fill_id)
                .limit(limit)
            )
        )
        position_rows = tuple(
            self.session.scalars(
                select(PaperPositionRecord)
                .where(PaperPositionRecord.entry_order_id.in_(order_ids or [""]))
                .order_by(PaperPositionRecord.opened_at, PaperPositionRecord.position_id)
                .limit(limit)
            )
        )
        position_ids = [row.position_id for row in position_rows]
        exit_rows = tuple(
            self.session.scalars(
                select(PaperExitDecisionRecord)
                .where(PaperExitDecisionRecord.position_id.in_(position_ids or [""]))
                .order_by(
                    PaperExitDecisionRecord.decided_at,
                    PaperExitDecisionRecord.exit_decision_id,
                )
                .limit(limit)
            )
        )
        journal_rows = tuple(
            self.session.scalars(
                select(PaperJournalEntryRecord)
                .where(
                    or_(
                        PaperJournalEntryRecord.command_id == command_id,
                        PaperJournalEntryRecord.order_id.in_(order_ids or [""]),
                        PaperJournalEntryRecord.fill_id.in_(
                            [row.fill_id for row in fill_rows] or [""]
                        ),
                        PaperJournalEntryRecord.position_id.in_(position_ids or [""]),
                        PaperJournalEntryRecord.exit_decision_id.in_(
                            [row.exit_decision_id for row in exit_rows] or [""]
                        ),
                    )
                )
                .order_by(
                    PaperJournalEntryRecord.occurred_at,
                    PaperJournalEntryRecord.journal_entry_id,
                )
                .limit(limit)
            )
        )
        graph = PaperCommandGraph(
            command,
            tuple(map(orm_values_to_paper_order, order_rows)),
            tuple(map(orm_values_to_paper_fill, fill_rows)),
            tuple(map(orm_values_to_paper_position, position_rows)),
            tuple(map(orm_values_to_paper_exit_decision, exit_rows)),
            tuple(map(orm_values_to_paper_event, journal_rows)),
        )
        return result(RepositoryOutcome.EXISTING_IDEMPOTENT, graph)


class JournalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append_or_get_journal_entry(
        self, entry: PaperDomainEvent, **links: str | None
    ) -> RepositoryResult[PaperDomainEvent]:
        key = journal_event_idempotency_key(
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            causation_id=entry.causation_id,
            event_type=entry.event_type,
        )
        row = self.session.scalar(
            select(PaperJournalEntryRecord)
            .where(PaperJournalEntryRecord.idempotency_key == key)
            .limit(1)
        )
        if row:
            return _same(orm_values_to_paper_event(row), entry, journal_semantic_tuple)
        try:
            with self.session.begin_nested():
                self.session.add(PaperJournalEntryRecord(**_journal_values(entry, **links)))
                self.session.flush()
        except IntegrityError:
            row = self.session.scalar(
                select(PaperJournalEntryRecord)
                .where(PaperJournalEntryRecord.idempotency_key == key)
                .limit(1)
            )
            if row:
                return _same(orm_values_to_paper_event(row), entry, journal_semantic_tuple)
            return result(RepositoryOutcome.CONSTRAINT_VIOLATION)
        return result(RepositoryOutcome.CREATED, entry)

    def list_journal_for_aggregate(
        self, aggregate_type: str, aggregate_id: str, *, limit: int = 100
    ) -> RepositoryResult[tuple[PaperDomainEvent, ...]]:
        if limit < 1 or limit > MAX_JOURNAL_ROWS:
            return result(
                RepositoryOutcome.CONSTRAINT_VIOLATION,
                reason_code="PAPER_REPOSITORY_LIMIT_INVALID",
            )
        rows = self.session.scalars(
            select(PaperJournalEntryRecord)
            .where(
                PaperJournalEntryRecord.aggregate_type == aggregate_type,
                PaperJournalEntryRecord.aggregate_id == aggregate_id,
            )
            .order_by(
                PaperJournalEntryRecord.aggregate_version,
                PaperJournalEntryRecord.occurred_at,
                PaperJournalEntryRecord.journal_entry_id,
            )
            .limit(limit)
        )
        return result(
            RepositoryOutcome.EXISTING_IDEMPOTENT,
            tuple(map(orm_values_to_paper_event, rows)),
        )


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_order(self, order_id: str) -> PaperOrder | None:
        row = self.session.get(PaperOrderRecord, order_id)
        return orm_values_to_paper_order(row) if row else None

    def get_order_by_idempotency_key(self, key: str) -> PaperOrder | None:
        row = self.session.scalar(
            select(PaperOrderRecord)
            .where(PaperOrderRecord.idempotency_key == key)
            .limit(1)
        )
        return orm_values_to_paper_order(row) if row else None

    def create_or_get_order(
        self,
        command: PaperExecutionCommand,
        order: PaperOrder,
        event: PaperDomainEvent,
        journal_entry: PaperDomainEvent,
        *,
        order_role: str = "ENTRY",
    ) -> RepositoryResult[PaperOrder]:
        existing = self.get_order_by_idempotency_key(order.idempotency_key)
        if existing:
            compared = _same(existing, order, order_semantic_tuple)
            if compared.outcome is not RepositoryOutcome.EXISTING_IDEMPOTENT:
                return compared
            key = _order_event_values(
                event, previous_state=None, state=order.state
            )["idempotency_key"]
            existing_event = self.session.scalar(
                select(PaperOrderEventRecord)
                .where(PaperOrderEventRecord.idempotency_key == key)
                .limit(1)
            )
            journal_key = _journal_values(
                journal_entry,
                command_id=command.command_id,
                order_id=order.order_id,
            )["idempotency_key"]
            existing_journal = self.session.scalar(
                select(PaperJournalEntryRecord)
                .where(PaperJournalEntryRecord.idempotency_key == journal_key)
                .limit(1)
            )
            if (
                existing_event is None
                or existing_journal is None
                or journal_semantic_tuple(orm_values_to_paper_event(existing_journal))
                != journal_semantic_tuple(journal_entry)
            ):
                return result(RepositoryOutcome.IDEMPOTENCY_CONFLICT, existing)
            return compared
        if order.command_id != command.command_id:
            return result(RepositoryOutcome.INVALID_STATE)
        try:
            with self.session.begin_nested():
                self.session.add(
                    PaperOrderRecord(
                        **paper_order_to_orm_values(order, order_role=order_role)
                    )
                )
                self.session.flush()
                self.session.add(
                    PaperOrderEventRecord(
                        **_order_event_values(event, previous_state=None, state=order.state)
                    )
                )
                self.session.flush()
                self.session.add(
                    PaperJournalEntryRecord(
                        **_journal_values(
                            journal_entry,
                            command_id=command.command_id,
                            order_id=order.order_id,
                        )
                    )
                )
                self.session.flush()
        except IntegrityError as exception:
            existing = self.get_order_by_idempotency_key(order.idempotency_key)
            if existing:
                return _same(existing, order, order_semantic_tuple)
            failure = classify_database_failure(exception)
            return result(failure.outcome, reason_code=failure.reason_code)
        return result(RepositoryOutcome.CREATED, order)

    def transition_order(
        self,
        order_id: str,
        expected_version: int,
        target_state: PaperOrderState,
        event: PaperDomainEvent | None,
        journal_entry: PaperDomainEvent | None,
        *,
        occurred_at=None,
        reason_code: PaperReasonCode | None = None,
    ) -> RepositoryResult[PaperOrder]:
        row = self.session.scalar(
            select(PaperOrderRecord)
            .where(PaperOrderRecord.order_id == order_id)
            .with_for_update()
        )
        if not row:
            return result(RepositoryOutcome.NOT_FOUND)
        current = orm_values_to_paper_order(row)
        if event:
            event_values = _order_event_values(
                event, previous_state=current.state, state=target_state
            )
            existing_event = self.session.scalar(
                select(PaperOrderEventRecord)
                .where(PaperOrderEventRecord.idempotency_key == event_values["idempotency_key"])
                .limit(1)
            )
            if existing_event:
                matches = (
                    existing_event.order_event_id == event.event_id
                    and existing_event.event_type == event.event_type.value
                    and existing_event.to_state == target_state.value
                    and existing_event.aggregate_version == event.aggregate_version
                    and existing_event.correlation_id == event.correlation_id
                    and existing_event.causation_id == event.causation_id
                    and existing_event.reason_code == event.reason_code.value
                    and existing_event.occurred_at == event.occurred_at
                )
                return result(
                    RepositoryOutcome.EXISTING_IDEMPOTENT
                    if matches
                    else RepositoryOutcome.IDEMPOTENCY_CONFLICT,
                    current,
                )
        if current.version != expected_version:
            return result(RepositoryOutcome.STALE_VERSION)
        try:
            changed = transition_order(
                current,
                target_state,
                expected_version=expected_version,
                occurred_at=occurred_at,
                event_id=event.event_id if event else None,
                reason_code=reason_code,
            )
        except PaperDomainError as exception:
            return _domain_failure(exception)
        if not changed.applied or changed.order.version != current.version + 1:
            return result(RepositoryOutcome.INTERNAL_INVARIANT_FAILURE)
        canonical_event = changed.events[0] if len(changed.events) == 1 else None
        if (
            canonical_event is None
            or event is None
            or journal_entry is None
            or journal_semantic_tuple(event) != journal_semantic_tuple(canonical_event)
            or journal_semantic_tuple(journal_entry) != journal_semantic_tuple(canonical_event)
        ):
            return result(
                RepositoryOutcome.INVALID_STATE,
                current,
                reason_code="PAPER_ORDER_TRANSITION_EVENT_MISMATCH",
            )
        try:
            with self.session.begin_nested():
                for name, value in paper_order_to_orm_values(
                    changed.order, order_role=row.order_role
                ).items():
                    if name not in {"order_id", "command_id", "idempotency_key", "order_role", "mode"}:
                        setattr(row, name, value)
                self.session.add(
                    PaperOrderEventRecord(
                        **_order_event_values(
                            canonical_event,
                            previous_state=current.state,
                            state=changed.order.state,
                        )
                    )
                )
                self.session.add(
                    PaperJournalEntryRecord(
                        **_journal_values(
                            canonical_event,
                            command_id=current.command_id,
                            order_id=current.order_id,
                        )
                    )
                )
                self.session.flush()
        except IntegrityError as exception:
            failure = classify_database_failure(exception)
            return result(failure.outcome, reason_code=failure.reason_code)
        return result(RepositoryOutcome.UPDATED, changed.order)


class PositionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_position(self, position_id: str) -> PaperPosition | None:
        row = self.session.get(PaperPositionRecord, position_id)
        return orm_values_to_paper_position(row) if row else None

    def get_active_position(self, mode, symbol: str) -> PaperPosition | None:
        row = self.session.scalar(
            select(PaperPositionRecord)
            .where(
                PaperPositionRecord.mode == getattr(mode, "value", mode),
                PaperPositionRecord.symbol == symbol.upper(),
                PaperPositionRecord.state.in_(("OPEN", "CLOSING")),
            )
            .order_by(PaperPositionRecord.opened_at, PaperPositionRecord.position_id)
            .limit(1)
        )
        return orm_values_to_paper_position(row) if row else None

    def begin_closing(
        self,
        position_id: str,
        expected_version: int,
        exit_decision_id: str,
        occurred_at,
        journal_entry: PaperDomainEvent | None = None,
    ) -> RepositoryResult[PaperPosition]:
        row = self.session.scalar(
            select(PaperPositionRecord)
            .where(PaperPositionRecord.position_id == position_id)
            .with_for_update()
        )
        if not row:
            return result(RepositoryOutcome.NOT_FOUND)
        current = orm_values_to_paper_position(row)
        if current.version != expected_version:
            return result(RepositoryOutcome.STALE_VERSION)
        try:
            changed = begin_closing(
                current,
                expected_version=expected_version,
                exit_decision_id=exit_decision_id,
                occurred_at=occurred_at,
            )
        except PaperDomainError as exception:
            return _domain_failure(exception)
        _copy_position(row, changed.position)
        if journal_entry:
            self.session.add(
                PaperJournalEntryRecord(
                    **_journal_values(
                        journal_entry,
                        position_id=position_id,
                    )
                )
            )
        self.session.flush()
        return result(RepositoryOutcome.UPDATED, changed.position)

    def fail_position(
        self,
        position_id: str,
        expected_version: int,
        occurred_at,
        event: PaperDomainEvent,
    ) -> RepositoryResult[PaperPosition]:
        row = self.session.scalar(
            select(PaperPositionRecord)
            .where(PaperPositionRecord.position_id == position_id)
            .with_for_update()
        )
        if not row:
            return result(RepositoryOutcome.NOT_FOUND)
        current = orm_values_to_paper_position(row)
        try:
            changed = domain_fail_position(
                current,
                expected_version=expected_version,
                occurred_at=occurred_at,
                event_id=event.event_id,
                reason_code=event.reason_code,
            )
        except PaperDomainError as exception:
            return _domain_failure(exception)
        _copy_position(row, changed.position)
        self.session.add(
            PaperJournalEntryRecord(
                **_journal_values(event, position_id=position_id)
            )
        )
        self.session.flush()
        return result(RepositoryOutcome.UPDATED, changed.position)


class ExitRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_get_exit_decision(
        self,
        position_id: str,
        expected_position_version: int,
        decision: PaperExitDecision,
        event: PaperDomainEvent,
        journal_entry: PaperDomainEvent,
    ) -> RepositoryResult[PaperExitDecision]:
        position_row = self.session.scalar(
            select(PaperPositionRecord)
            .where(PaperPositionRecord.position_id == position_id)
            .with_for_update()
        )
        if not position_row:
            return result(RepositoryOutcome.NOT_FOUND)
        existing_row = self.session.scalar(
            select(PaperExitDecisionRecord)
            .where(PaperExitDecisionRecord.idempotency_key == decision.idempotency_key)
            .limit(1)
        )
        if existing_row:
            compared = _same(
                orm_values_to_paper_exit_decision(existing_row),
                decision,
                exit_semantic_tuple,
            )
            if compared.outcome is not RepositoryOutcome.EXISTING_IDEMPOTENT:
                return compared
            journal_key = _journal_values(
                journal_entry,
                position_id=position_id,
                exit_decision_id=decision.exit_decision_id,
            )["idempotency_key"]
            journal_row = self.session.scalar(
                select(PaperJournalEntryRecord)
                .where(PaperJournalEntryRecord.idempotency_key == journal_key)
                .limit(1)
            )
            if (
                journal_row is None
                or journal_semantic_tuple(orm_values_to_paper_event(journal_row))
                != journal_semantic_tuple(journal_entry)
            ):
                return result(RepositoryOutcome.IDEMPOTENCY_CONFLICT, decision)
            return compared
        current = orm_values_to_paper_position(position_row)
        if current.version != expected_position_version:
            return result(RepositoryOutcome.STALE_VERSION)
        if (
            decision.position_id != position_id
            or decision.position_version != current.version
            or decision.requested_close_quantity != current.remaining_quantity
        ):
            return result(RepositoryOutcome.INVALID_STATE)
        try:
            changed = begin_closing(
                current,
                expected_version=expected_position_version,
                exit_decision_id=decision.exit_decision_id,
                occurred_at=decision.decided_at,
            )
        except PaperDomainError as exception:
            return _domain_failure(exception)
        try:
            with self.session.begin_nested():
                self.session.add(
                    PaperExitDecisionRecord(
                        **paper_exit_decision_to_orm_values(decision)
                    )
                )
                _copy_position(position_row, changed.position)
                self.session.add(
                    PaperJournalEntryRecord(
                        **_journal_values(
                            journal_entry,
                            position_id=position_id,
                            exit_decision_id=decision.exit_decision_id,
                        )
                    )
                )
                self.session.flush()
        except IntegrityError as exception:
            existing_row = self.session.scalar(
                select(PaperExitDecisionRecord)
                .where(PaperExitDecisionRecord.idempotency_key == decision.idempotency_key)
                .limit(1)
            )
            if existing_row:
                return _same(
                    orm_values_to_paper_exit_decision(existing_row),
                    decision,
                    exit_semantic_tuple,
                )
            failure = classify_database_failure(exception)
            return result(failure.outcome, reason_code=failure.reason_code)
        return result(RepositoryOutcome.CREATED, decision)


def _copy_position(row: PaperPositionRecord, position: PaperPosition) -> None:
    for name, value in paper_position_to_orm_values(position).items():
        if name not in {"position_id", "entry_order_id", "entry_fill_id", "created_at"}:
            setattr(row, name, value)


class PaperRepositories:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.commands = CommandRepository(session)
        self.orders = OrderRepository(session)
        self.positions = PositionRepository(session)
        self.exits = ExitRepository(session)
        self.journal = JournalRepository(session)
        self.fault_injector: Callable[[str], None] | None = None

    def _fault(self, stage: str) -> None:
        if self.fault_injector is not None:
            self.fault_injector(stage)

    def apply_entry_fill_and_open_position(
        self,
        order_id: str,
        expected_order_version: int,
        fill: PaperFill,
        position: PaperPosition,
        order_event: PaperDomainEvent,
        position_event: PaperDomainEvent,
        journal_entries: tuple[PaperDomainEvent, ...],
    ) -> RepositoryResult[EntryFillGraph]:
        order_row = self.session.scalar(
            select(PaperOrderRecord)
            .where(PaperOrderRecord.order_id == order_id)
            .with_for_update()
        )
        if not order_row:
            return result(RepositoryOutcome.NOT_FOUND)
        current_order = orm_values_to_paper_order(order_row)
        existing_fill_row = self.session.scalar(
            select(PaperFillRecord)
            .where(PaperFillRecord.idempotency_key == fill.idempotency_key)
            .limit(1)
        )
        if existing_fill_row:
            existing_fill = orm_values_to_paper_fill(existing_fill_row)
            if fill_semantic_tuple(existing_fill) != fill_semantic_tuple(fill):
                return result(RepositoryOutcome.IDEMPOTENCY_CONFLICT)
            position_row = self.session.scalar(
                select(PaperPositionRecord)
                .where(PaperPositionRecord.entry_fill_id == existing_fill.fill_id)
                .limit(1)
            )
            if (
                current_order.state is PaperOrderState.FILLED
                and position_row is not None
            ):
                existing_position = orm_values_to_paper_position(position_row)
                if existing_position != position:
                    return result(RepositoryOutcome.IDEMPOTENCY_CONFLICT)
                return result(
                    RepositoryOutcome.EXISTING_IDEMPOTENT,
                    EntryFillGraph(
                        current_order,
                        existing_fill,
                        existing_position,
                    ),
                )
            return result(RepositoryOutcome.INTERNAL_INVARIANT_FAILURE)
        if current_order.state is PaperOrderState.FILLED:
            return result(RepositoryOutcome.INVALID_STATE)
        if current_order.version != expected_order_version:
            return result(RepositoryOutcome.STALE_VERSION)
        command_row = self.session.scalar(
            select(PaperExecutionCommandRecord)
            .where(PaperExecutionCommandRecord.command_id == current_order.command_id)
            .with_for_update()
        )
        if not command_row:
            return result(RepositoryOutcome.INTERNAL_INVARIANT_FAILURE)
        command = orm_values_to_paper_command(command_row)
        try:
            order_change = fill_order(
                current_order,
                fill,
                expected_version=expected_order_version,
                event_id=order_event.event_id,
            )
            position_change = apply_entry_fill(
                None,
                command,
                order_change.order,
                fill,
                position_id=position.position_id,
                event_id=position_event.event_id,
            )
        except PaperDomainError as exception:
            return _domain_failure(exception)
        if position_change.position != position:
            return result(
                RepositoryOutcome.INTERNAL_INVARIANT_FAILURE,
                reason_code="PAPER_REPOSITORY_POSITION_PROJECTION_MISMATCH",
            )
        try:
            with self.session.begin_nested():
                self.session.add(
                    PaperFillRecord(**paper_fill_to_orm_values(fill, fill_role="ENTRY"))
                )
                self.session.flush()
                self._fault("entry_after_fill")
                for name, value in paper_order_to_orm_values(
                    order_change.order, order_role=order_row.order_role
                ).items():
                    if name not in {"order_id", "command_id", "idempotency_key", "order_role", "mode"}:
                        setattr(order_row, name, value)
                self.session.flush()
                self._fault("entry_after_order")
                self.session.add(
                    PaperPositionRecord(**paper_position_to_orm_values(position))
                )
                self.session.flush()
                self._fault("entry_after_position")
                self.session.add(
                    PaperOrderEventRecord(
                        **_order_event_values(
                            order_event,
                            previous_state=current_order.state,
                            state=order_change.order.state,
                        )
                    )
                )
                self.session.flush()
                self._fault("entry_after_event")
                for entry in journal_entries:
                    self.session.add(
                        PaperJournalEntryRecord(
                            **_journal_values(
                                entry,
                                command_id=current_order.command_id,
                                order_id=order_id,
                                fill_id=fill.fill_id,
                                position_id=position.position_id,
                            )
                        )
                    )
                self.session.flush()
                self._fault("entry_after_journal")
        except IntegrityError as exception:
            failure = classify_database_failure(exception)
            return result(failure.outcome, reason_code=failure.reason_code)
        return result(
            RepositoryOutcome.CREATED,
            EntryFillGraph(order_change.order, fill, position),
        )

    def apply_close_fill_and_close_position(
        self,
        exit_decision_id: str,
        position_id: str,
        expected_position_version: int,
        close_order_id: str,
        expected_order_version: int,
        fill: PaperFill,
        events: tuple[PaperDomainEvent, ...],
        journal_entries: tuple[PaperDomainEvent, ...],
    ) -> RepositoryResult[CloseFillGraph]:
        order_row = self.session.scalar(
            select(PaperOrderRecord)
            .where(PaperOrderRecord.order_id == close_order_id)
            .with_for_update()
        )
        if not order_row:
            return result(RepositoryOutcome.NOT_FOUND)
        position_row = self.session.scalar(
            select(PaperPositionRecord)
            .where(PaperPositionRecord.position_id == position_id)
            .with_for_update()
        )
        if not position_row:
            return result(RepositoryOutcome.NOT_FOUND)
        decision = self.session.get(PaperExitDecisionRecord, exit_decision_id)
        if not decision or decision.position_id != position_id:
            return result(RepositoryOutcome.INVALID_STATE)
        order = orm_values_to_paper_order(order_row)
        position = orm_values_to_paper_position(position_row)
        existing_fill_row = self.session.scalar(
            select(PaperFillRecord)
            .where(PaperFillRecord.idempotency_key == fill.idempotency_key)
            .limit(1)
        )
        if existing_fill_row:
            existing_fill = orm_values_to_paper_fill(existing_fill_row)
            if fill_semantic_tuple(existing_fill) != fill_semantic_tuple(fill):
                return result(RepositoryOutcome.IDEMPOTENCY_CONFLICT)
            if (
                order.state is PaperOrderState.FILLED
                and position.state is PaperPositionState.CLOSED
                and position.exit_fill_id == existing_fill.fill_id
            ):
                return result(
                    RepositoryOutcome.EXISTING_IDEMPOTENT,
                    CloseFillGraph(order, existing_fill, position),
                )
            return result(RepositoryOutcome.INTERNAL_INVARIANT_FAILURE)
        if (
            order.state is PaperOrderState.FILLED
            or position.state is PaperPositionState.CLOSED
        ):
            return result(RepositoryOutcome.INVALID_STATE)
        if order.version != expected_order_version or position.version != expected_position_version:
            return result(RepositoryOutcome.STALE_VERSION)
        order_event = next(
            (e for e in events if e.aggregate_type == "paper_order"), None
        )
        position_event = next(
            (e for e in events if e.aggregate_type == "paper_position"), None
        )
        if not order_event or not position_event:
            return result(RepositoryOutcome.INTERNAL_INVARIANT_FAILURE)
        try:
            order_change = fill_order(
                order,
                fill,
                expected_version=expected_order_version,
                event_id=order_event.event_id,
            )
            position_change = apply_close_fill(
                position,
                fill,
                expected_version=expected_position_version,
                event_id=position_event.event_id,
            )
        except PaperDomainError as exception:
            return _domain_failure(exception)
        try:
            with self.session.begin_nested():
                self.session.add(
                    PaperFillRecord(**paper_fill_to_orm_values(fill, fill_role="EXIT"))
                )
                self.session.flush()
                self._fault("close_after_fill")
                for name, value in paper_order_to_orm_values(
                    order_change.order, order_role=order_row.order_role
                ).items():
                    if name not in {"order_id", "command_id", "idempotency_key", "order_role", "mode"}:
                        setattr(order_row, name, value)
                self.session.flush()
                self._fault("close_after_order")
                _copy_position(position_row, position_change.position)
                self.session.flush()
                self._fault("close_after_position")
                self.session.add(
                    PaperOrderEventRecord(
                        **_order_event_values(
                            order_event,
                            previous_state=order.state,
                            state=order_change.order.state,
                        )
                    )
                )
                self.session.flush()
                self._fault("close_after_event")
                for entry in journal_entries:
                    self.session.add(
                        PaperJournalEntryRecord(
                            **_journal_values(
                                entry,
                                command_id=order.command_id,
                                order_id=close_order_id,
                                fill_id=fill.fill_id,
                                position_id=position_id,
                                exit_decision_id=exit_decision_id,
                            )
                        )
                    )
                self.session.flush()
                self._fault("close_after_journal")
        except IntegrityError as exception:
            failure = classify_database_failure(exception)
            return result(failure.outcome, reason_code=failure.reason_code)
        return result(
            RepositoryOutcome.UPDATED,
            CloseFillGraph(order_change.order, fill, position_change.position),
        )
