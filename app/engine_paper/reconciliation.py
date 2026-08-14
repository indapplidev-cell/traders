"""Bounded, fail-closed, read-only reconciliation for PAPER persistence.

The schema gate is intentionally the first database operation.  A target that
is not at revision 0012 returns ``PAPER_SCHEMA_NOT_DEPLOYED`` without issuing
any query against a PAPER table.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Any, Callable, Final, Mapping, Protocol, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session


PAPER_RECONCILIATION_SCHEMA_VERSION: Final = "PAPER_RECONCILIATION_REPORT_V1"
EXPECTED_SCHEMA_HEAD: Final = (
    "0015_trading_universe_activation"
)
MAX_SAFE_ID_LENGTH: Final = 128
MAX_SAFE_REPORT_BYTES: Final = 65_536
PAPER_TABLES: Final = (
    "paper_execution_commands",
    "paper_orders",
    "paper_fills",
    "paper_positions",
    "paper_exit_evaluation_cursors",
    "paper_exit_decisions",
    "paper_order_events",
    "paper_journal_entries",
)
PRIMARY_KEYS: Final = {
    "paper_execution_commands": "command_id",
    "paper_orders": "order_id",
    "paper_fills": "fill_id",
    "paper_positions": "position_id",
    "paper_exit_evaluation_cursors": "cursor_id",
    "paper_exit_decisions": "exit_decision_id",
    "paper_order_events": "order_event_id",
    "paper_journal_entries": "journal_entry_id",
}
ENTITY_NAMES: Final = {
    "paper_execution_commands": "commands",
    "paper_orders": "orders",
    "paper_fills": "fills",
    "paper_positions": "positions",
    "paper_exit_evaluation_cursors": "cursors",
    "paper_exit_decisions": "exit_decisions",
    "paper_order_events": "events",
    "paper_journal_entries": "journal_rows",
}
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|TRUNCATE|CREATE|ALTER|DROP|GRANT|REVOKE|COPY|CALL)\b",
    re.IGNORECASE,
)


def _safe_id(value: str | None, *, required: bool = False) -> None:
    if value is None and not required:
        return
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_SAFE_ID_LENGTH
        or "://" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("INVALID_SAFE_ID")


class PaperReconciliationInvariant(StrEnum):
    COMMAND_SEMANTIC_IDENTITY = "COMMAND_SEMANTIC_IDENTITY"
    APPROVAL_LINKAGE = "APPROVAL_LINKAGE"
    ORDER_CAUSAL_IDENTITY = "ORDER_CAUSAL_IDENTITY"
    ORDER_EVENT_SEQUENCE = "ORDER_EVENT_SEQUENCE"
    ORDER_FILL_RELATION = "ORDER_FILL_RELATION"
    ORDER_POSITION_COMPATIBILITY = "ORDER_POSITION_COMPATIBILITY"
    FILL_IDENTITY_AND_ROLE = "FILL_IDENTITY_AND_ROLE"
    POSITION_LIFECYCLE = "POSITION_LIFECYCLE"
    EXIT_DECISION_CAUSALITY = "EXIT_DECISION_CAUSALITY"
    CURSOR_PROGRESS = "CURSOR_PROGRESS"
    JOURNAL_COMPLETENESS = "JOURNAL_COMPLETENESS"
    ACCOUNTING_EXACTLY_ONCE = "ACCOUNTING_EXACTLY_ONCE"
    VERSION_MONOTONICITY = "VERSION_MONOTONICITY"
    ORPHAN_FREEDOM = "ORPHAN_FREEDOM"


class PaperReconciliationSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class PaperReconciliationOutcome(StrEnum):
    HEALTHY = "HEALTHY"
    INCONSISTENT = "INCONSISTENT"
    PAPER_SCHEMA_NOT_DEPLOYED = "PAPER_SCHEMA_NOT_DEPLOYED"
    TARGET_REJECTED = "TARGET_REJECTED"
    READ_ONLY_POLICY_VIOLATION = "READ_ONLY_POLICY_VIOLATION"
    BOUNDED_LIMIT_EXCEEDED = "BOUNDED_LIMIT_EXCEEDED"
    CANCELLED = "CANCELLED"
    SAFE_FAILURE = "SAFE_FAILURE"


class PaperReconciliationExitCode(IntEnum):
    HEALTHY = 0
    INCONSISTENT = 10
    PAPER_SCHEMA_NOT_DEPLOYED = 11
    TARGET_REJECTED = 12
    READ_ONLY_POLICY_VIOLATION = 13
    BOUNDED_LIMIT_EXCEEDED = 14
    CANCELLED = 15
    SAFE_FAILURE = 16


EXIT_CODES: Final = {
    PaperReconciliationOutcome.HEALTHY: PaperReconciliationExitCode.HEALTHY,
    PaperReconciliationOutcome.INCONSISTENT: PaperReconciliationExitCode.INCONSISTENT,
    PaperReconciliationOutcome.PAPER_SCHEMA_NOT_DEPLOYED: PaperReconciliationExitCode.PAPER_SCHEMA_NOT_DEPLOYED,
    PaperReconciliationOutcome.TARGET_REJECTED: PaperReconciliationExitCode.TARGET_REJECTED,
    PaperReconciliationOutcome.READ_ONLY_POLICY_VIOLATION: PaperReconciliationExitCode.READ_ONLY_POLICY_VIOLATION,
    PaperReconciliationOutcome.BOUNDED_LIMIT_EXCEEDED: PaperReconciliationExitCode.BOUNDED_LIMIT_EXCEEDED,
    PaperReconciliationOutcome.CANCELLED: PaperReconciliationExitCode.CANCELLED,
    PaperReconciliationOutcome.SAFE_FAILURE: PaperReconciliationExitCode.SAFE_FAILURE,
}


@dataclass(frozen=True, slots=True)
class PaperReconciliationScope:
    position_id: str | None = None
    command_id: str | None = None
    symbol: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    full_isolated_fixture: bool = False
    max_positions: int = 100
    max_orders: int = 300
    max_fills: int = 300
    max_events: int = 1_500
    max_journal_rows: int = 2_000
    max_cursors: int = 100
    max_exit_decisions: int = 100
    max_commands: int = 100
    max_findings: int = 200
    max_time_range_seconds: int = 86_400 * 31

    def __post_init__(self) -> None:
        for value in (self.position_id, self.command_id, self.symbol):
            _safe_id(value)
        limits = (
            self.max_positions,
            self.max_orders,
            self.max_fills,
            self.max_events,
            self.max_journal_rows,
            self.max_cursors,
            self.max_exit_decisions,
            self.max_commands,
            self.max_findings,
            self.max_time_range_seconds,
        )
        if any(not isinstance(value, int) or value <= 0 for value in limits):
            raise ValueError("INVALID_SCOPE_LIMIT")
        if (self.started_at is None) != (self.ended_at is None):
            raise ValueError("TIME_RANGE_MUST_HAVE_BOTH_BOUNDARIES")
        if self.started_at is not None:
            if self.started_at.tzinfo is None or self.ended_at.tzinfo is None:
                raise ValueError("TIME_RANGE_MUST_BE_AWARE")
            seconds = (self.ended_at - self.started_at).total_seconds()
            if seconds < 0 or seconds > self.max_time_range_seconds:
                raise ValueError("TIME_RANGE_LIMIT_EXCEEDED")

    def safe_summary(self) -> Mapping[str, Any]:
        return {
            "position_id": self.position_id,
            "command_id": self.command_id,
            "symbol": self.symbol,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "full_isolated_fixture": self.full_isolated_fixture,
        }


@dataclass(frozen=True, slots=True)
class PaperReconciliationRequest:
    request_id: str
    correlation_id: str
    target_class: str
    target_identity: str
    expected_schema_head: str
    scope: PaperReconciliationScope
    read_only_reconcile: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.request_id,
            self.correlation_id,
            self.target_class,
            self.target_identity,
            self.expected_schema_head,
        ):
            _safe_id(value, required=True)
        if self.expected_schema_head != EXPECTED_SCHEMA_HEAD:
            raise ValueError("UNSUPPORTED_EXPECTED_SCHEMA_HEAD")
        if not self.read_only_reconcile:
            raise ValueError("READ_ONLY_RECONCILIATION_REQUIRED")


@dataclass(frozen=True, slots=True)
class PaperReconciliationFinding:
    code: str
    invariant: PaperReconciliationInvariant
    severity: PaperReconciliationSeverity
    entity_type: str
    safe_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _safe_id(self.code, required=True)
        _safe_id(self.entity_type, required=True)
        if len(self.safe_ids) > 8:
            raise ValueError("TOO_MANY_SAFE_IDS")
        for value in self.safe_ids:
            _safe_id(value, required=True)


@dataclass(frozen=True, slots=True)
class PaperReconciliationEntitySummary:
    commands: int = 0
    orders: int = 0
    fills: int = 0
    positions: int = 0
    cursors: int = 0
    exit_decisions: int = 0
    events: int = 0
    journal_rows: int = 0


@dataclass(frozen=True, slots=True)
class PaperReconciliationResult:
    request_id: str
    correlation_id: str
    target_class: str
    schema_head: str | None
    scope: PaperReconciliationScope
    outcome: PaperReconciliationOutcome
    entity_summary: PaperReconciliationEntitySummary
    findings: tuple[PaperReconciliationFinding, ...]
    read_only: bool
    query_count: int
    paper_table_queries: int
    business_mutations: int
    schema_mutations: int
    duration_ms: int
    reason_code: str

    @property
    def exit_code(self) -> PaperReconciliationExitCode:
        return EXIT_CODES[self.outcome]

    @property
    def severity_counts(self) -> Mapping[str, int]:
        counts = Counter(finding.severity.value for finding in self.findings)
        return {severity.value: counts[severity.value] for severity in PaperReconciliationSeverity}


class PaperReconciliationReader(Protocol):
    query_count: int
    paper_table_queries: int
    business_mutations: int
    schema_mutations: int

    def begin_read_only(self) -> bool: ...
    def schema_head(self) -> str | None: ...
    def read(self, table: str, limit: int) -> Sequence[Mapping[str, Any]]: ...
    def close(self) -> None: ...


class ReadOnlyPolicyViolation(RuntimeError):
    pass


class SqlAlchemyPaperReconciliationReader:
    """Whitelisted SQLAlchemy reader with a PostgreSQL read-only transaction."""

    def __init__(self, session: Session, *, require_postgresql_read_only: bool = True):
        self.session = session
        self.require_postgresql_read_only = require_postgresql_read_only
        self.query_count = 0
        self.paper_table_queries = 0
        self.business_mutations = 0
        self.schema_mutations = 0
        self._closed = False

    def _execute(self, statement: str, parameters: Mapping[str, Any] | None = None):
        if _FORBIDDEN_SQL.search(statement):
            if re.search(r"\b(CREATE|ALTER|DROP|GRANT|REVOKE|TRUNCATE)\b", statement, re.I):
                self.schema_mutations += 1
            else:
                self.business_mutations += 1
            raise ReadOnlyPolicyViolation("MUTATING_SQL_REJECTED")
        normalized = " ".join(statement.upper().split())
        if not (
            normalized.startswith("SELECT")
            or normalized.startswith("SHOW")
            or normalized.startswith("SET TRANSACTION READ ONLY")
        ):
            raise ReadOnlyPolicyViolation("NON_ALLOWLISTED_SQL_REJECTED")
        self.query_count += 1
        return self.session.execute(text(statement), parameters or {})

    def begin_read_only(self) -> bool:
        dialect = self.session.get_bind().dialect.name
        if dialect != "postgresql":
            return not self.require_postgresql_read_only
        self._execute("SET TRANSACTION READ ONLY")
        value = self._execute("SHOW transaction_read_only").scalar_one()
        return str(value).lower() == "on"

    def schema_head(self) -> str | None:
        return self._execute("SELECT version_num FROM alembic_version").scalar_one_or_none()

    def read(self, table: str, limit: int) -> Sequence[Mapping[str, Any]]:
        if table not in PAPER_TABLES:
            raise ReadOnlyPolicyViolation("TABLE_NOT_ALLOWLISTED")
        primary_key = PRIMARY_KEYS[table]
        self.paper_table_queries += 1
        return tuple(
            dict(row)
            for row in self._execute(
                f"SELECT * FROM {table} ORDER BY {primary_key} LIMIT :bounded_limit",
                {"bounded_limit": limit + 1},
            ).mappings()
        )

    def close(self) -> None:
        if self._closed:
            return
        self.session.rollback()
        self._closed = True


def _duplicates(rows: Sequence[Mapping[str, Any]], key: str) -> set[str]:
    values = [str(row[key]) for row in rows if row.get(key) is not None]
    return {value for value, count in Counter(values).items() if count > 1}


def _bounded_ids(*values: Any) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value is not None:
            rendered = str(value)[:MAX_SAFE_ID_LENGTH]
            if rendered and "://" not in rendered and rendered not in result:
                result.append(rendered)
    return tuple(result[:8])


_SEVERITY: Final = {
    "OPEN_WITHOUT_CURSOR": PaperReconciliationSeverity.HIGH,
    "OPEN_WITHOUT_ENTRY_FILL": PaperReconciliationSeverity.CRITICAL,
    "CLOSING_WITHOUT_EXIT_DECISION": PaperReconciliationSeverity.CRITICAL,
    "CLOSING_WITHOUT_CLOSE_ORDER": PaperReconciliationSeverity.CRITICAL,
    "CLOSED_WITHOUT_CLOSE_FILL": PaperReconciliationSeverity.CRITICAL,
    "DUPLICATE_FILL": PaperReconciliationSeverity.CRITICAL,
    "DUPLICATE_SEMANTIC_ORDER": PaperReconciliationSeverity.HIGH,
    "DUPLICATE_TERMINAL_JOURNAL_ACCOUNTING": PaperReconciliationSeverity.CRITICAL,
    "DOUBLE_FEE": PaperReconciliationSeverity.CRITICAL,
    "DOUBLE_PNL": PaperReconciliationSeverity.CRITICAL,
    "ORPHAN_FILL": PaperReconciliationSeverity.HIGH,
    "ORPHAN_ORDER_EVENT": PaperReconciliationSeverity.HIGH,
    "ORPHAN_EXIT_DECISION": PaperReconciliationSeverity.HIGH,
    "ORPHAN_CURSOR": PaperReconciliationSeverity.HIGH,
    "ORPHAN_JOURNAL": PaperReconciliationSeverity.HIGH,
    "CURSOR_REGRESSION": PaperReconciliationSeverity.HIGH,
    "FUTURE_CURSOR": PaperReconciliationSeverity.HIGH,
    "INVALID_EVENT_ORDERING": PaperReconciliationSeverity.HIGH,
    "VERSION_REGRESSION": PaperReconciliationSeverity.HIGH,
    "CAUSAL_ID_MISMATCH": PaperReconciliationSeverity.HIGH,
    "WRONG_CLOSE_LINEAGE": PaperReconciliationSeverity.CRITICAL,
    "IMPOSSIBLE_ORDER_POSITION_COMBINATION": PaperReconciliationSeverity.CRITICAL,
    "MISSING_REQUIRED_EVENT": PaperReconciliationSeverity.HIGH,
    "COMMAND_SEMANTIC_IDENTITY_DUPLICATE": PaperReconciliationSeverity.HIGH,
    "APPROVAL_LINKAGE_INVALID": PaperReconciliationSeverity.CRITICAL,
    "FILL_ROLE_MISMATCH": PaperReconciliationSeverity.HIGH,
    "FINALIZED_ACCOUNTING_ON_NON_CLOSED_POSITION": PaperReconciliationSeverity.CRITICAL,
}


_INVARIANT: Final = {
    "OPEN_WITHOUT_CURSOR": PaperReconciliationInvariant.CURSOR_PROGRESS,
    "OPEN_WITHOUT_ENTRY_FILL": PaperReconciliationInvariant.POSITION_LIFECYCLE,
    "CLOSING_WITHOUT_EXIT_DECISION": PaperReconciliationInvariant.POSITION_LIFECYCLE,
    "CLOSING_WITHOUT_CLOSE_ORDER": PaperReconciliationInvariant.POSITION_LIFECYCLE,
    "CLOSED_WITHOUT_CLOSE_FILL": PaperReconciliationInvariant.POSITION_LIFECYCLE,
    "DUPLICATE_FILL": PaperReconciliationInvariant.FILL_IDENTITY_AND_ROLE,
    "DUPLICATE_SEMANTIC_ORDER": PaperReconciliationInvariant.ORDER_CAUSAL_IDENTITY,
    "DUPLICATE_TERMINAL_JOURNAL_ACCOUNTING": PaperReconciliationInvariant.ACCOUNTING_EXACTLY_ONCE,
    "DOUBLE_FEE": PaperReconciliationInvariant.ACCOUNTING_EXACTLY_ONCE,
    "DOUBLE_PNL": PaperReconciliationInvariant.ACCOUNTING_EXACTLY_ONCE,
    "ORPHAN_FILL": PaperReconciliationInvariant.ORPHAN_FREEDOM,
    "ORPHAN_ORDER_EVENT": PaperReconciliationInvariant.ORPHAN_FREEDOM,
    "ORPHAN_EXIT_DECISION": PaperReconciliationInvariant.ORPHAN_FREEDOM,
    "ORPHAN_CURSOR": PaperReconciliationInvariant.ORPHAN_FREEDOM,
    "ORPHAN_JOURNAL": PaperReconciliationInvariant.ORPHAN_FREEDOM,
    "CURSOR_REGRESSION": PaperReconciliationInvariant.CURSOR_PROGRESS,
    "FUTURE_CURSOR": PaperReconciliationInvariant.CURSOR_PROGRESS,
    "INVALID_EVENT_ORDERING": PaperReconciliationInvariant.ORDER_EVENT_SEQUENCE,
    "VERSION_REGRESSION": PaperReconciliationInvariant.VERSION_MONOTONICITY,
    "CAUSAL_ID_MISMATCH": PaperReconciliationInvariant.ORDER_CAUSAL_IDENTITY,
    "WRONG_CLOSE_LINEAGE": PaperReconciliationInvariant.EXIT_DECISION_CAUSALITY,
    "IMPOSSIBLE_ORDER_POSITION_COMBINATION": PaperReconciliationInvariant.ORDER_POSITION_COMPATIBILITY,
    "MISSING_REQUIRED_EVENT": PaperReconciliationInvariant.JOURNAL_COMPLETENESS,
    "COMMAND_SEMANTIC_IDENTITY_DUPLICATE": PaperReconciliationInvariant.COMMAND_SEMANTIC_IDENTITY,
    "APPROVAL_LINKAGE_INVALID": PaperReconciliationInvariant.APPROVAL_LINKAGE,
    "FILL_ROLE_MISMATCH": PaperReconciliationInvariant.FILL_IDENTITY_AND_ROLE,
    "FINALIZED_ACCOUNTING_ON_NON_CLOSED_POSITION": PaperReconciliationInvariant.ACCOUNTING_EXACTLY_ONCE,
}


class PaperReadOnlyReconciliationService:
    def __init__(
        self,
        reader_factory: Callable[[PaperReconciliationRequest], PaperReconciliationReader],
        *,
        cancellation_requested: Callable[[], bool] = lambda: False,
        fault_injector: Callable[[str], None] = lambda _phase: None,
        clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
    ):
        self._reader_factory = reader_factory
        self._cancelled = cancellation_requested
        self._fault = fault_injector
        self._clock_ms = clock_ms

    def reconcile(self, request: PaperReconciliationRequest) -> PaperReconciliationResult:
        started = time.perf_counter_ns()
        reader: PaperReconciliationReader | None = None
        schema_head: str | None = None
        rows: dict[str, Sequence[Mapping[str, Any]]] = {}

        def result(outcome: PaperReconciliationOutcome, reason: str, findings=()):
            counts = {name: len(rows.get(table, ())) for table, name in ENTITY_NAMES.items()}
            return PaperReconciliationResult(
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                target_class=request.target_class,
                schema_head=schema_head,
                scope=request.scope,
                outcome=outcome,
                entity_summary=PaperReconciliationEntitySummary(**counts),
                findings=tuple(findings),
                read_only=(
                    reader is not None
                    and reader.business_mutations == 0
                    and reader.schema_mutations == 0
                ),
                query_count=reader.query_count if reader else 0,
                paper_table_queries=reader.paper_table_queries if reader else 0,
                business_mutations=reader.business_mutations if reader else 0,
                schema_mutations=reader.schema_mutations if reader else 0,
                duration_ms=max(0, (time.perf_counter_ns() - started) // 1_000_000),
                reason_code=reason,
            )

        try:
            self._fault("before_target_validation")
            if request.target_class not in {"ISOLATED_POSTGRESQL_0012", "PRODUCTION_POSTGRESQL"}:
                return result(PaperReconciliationOutcome.TARGET_REJECTED, "TARGET_CLASS_REJECTED")
            if self._cancelled():
                return result(PaperReconciliationOutcome.CANCELLED, "CANCELLED_BEFORE_SCHEMA_GATE")
            reader = self._reader_factory(request)
            if not reader.begin_read_only():
                return result(PaperReconciliationOutcome.READ_ONLY_POLICY_VIOLATION, "DATABASE_READ_ONLY_NOT_PROVEN")
            schema_head = reader.schema_head()
            self._fault("after_schema_gate")
            if schema_head != request.expected_schema_head:
                return result(PaperReconciliationOutcome.PAPER_SCHEMA_NOT_DEPLOYED, "PAPER_SCHEMA_NOT_DEPLOYED")

            limits = {
                "paper_execution_commands": request.scope.max_commands,
                "paper_orders": request.scope.max_orders,
                "paper_fills": request.scope.max_fills,
                "paper_positions": request.scope.max_positions,
                "paper_exit_evaluation_cursors": request.scope.max_cursors,
                "paper_exit_decisions": request.scope.max_exit_decisions,
                "paper_order_events": request.scope.max_events,
                "paper_journal_entries": request.scope.max_journal_rows,
            }
            for table in PAPER_TABLES:
                if self._cancelled():
                    return result(PaperReconciliationOutcome.CANCELLED, f"CANCELLED_BEFORE_{ENTITY_NAMES[table].upper()}_READ")
                self._fault(f"during_{ENTITY_NAMES[table]}_read")
                table_rows = reader.read(table, limits[table])
                rows[table] = table_rows
                if len(table_rows) > limits[table]:
                    return result(PaperReconciliationOutcome.BOUNDED_LIMIT_EXCEEDED, f"{ENTITY_NAMES[table].upper()}_LIMIT_EXCEEDED")

            rows = self._scope_rows(rows, request.scope)

            self._fault("during_invariant_evaluation")
            findings = self._evaluate(rows, request.scope)
            if len(findings) > request.scope.max_findings:
                return result(PaperReconciliationOutcome.BOUNDED_LIMIT_EXCEEDED, "FINDING_LIMIT_EXCEEDED")
            self._fault("during_rendering")
            if self._cancelled():
                return result(PaperReconciliationOutcome.CANCELLED, "CANCELLED_AFTER_INCOMPLETE_SCAN")
            if findings:
                return result(PaperReconciliationOutcome.INCONSISTENT, "RECONCILIATION_FINDINGS_PRESENT", findings)
            return result(PaperReconciliationOutcome.HEALTHY, "RECONCILIATION_HEALTHY")
        except ReadOnlyPolicyViolation:
            return result(PaperReconciliationOutcome.READ_ONLY_POLICY_VIOLATION, "READ_ONLY_POLICY_VIOLATION")
        except Exception:
            return result(PaperReconciliationOutcome.SAFE_FAILURE, "RECONCILIATION_SAFE_FAILURE")
        finally:
            if reader is not None:
                try:
                    reader.close()
                except Exception:
                    pass

    @staticmethod
    def _scope_rows(
        source: Mapping[str, Sequence[Mapping[str, Any]]],
        scope: PaperReconciliationScope,
    ) -> dict[str, Sequence[Mapping[str, Any]]]:
        if (
            scope.full_isolated_fixture
            or (
                scope.position_id is None
                and scope.command_id is None
                and scope.symbol is None
                and scope.started_at is None
            )
        ):
            return {table: tuple(source[table]) for table in PAPER_TABLES}

        selected: dict[str, set[Any]] = {table: set() for table in PAPER_TABLES}

        def primary(table: str, row: Mapping[str, Any]) -> Any:
            return row.get(PRIMARY_KEYS[table])

        def in_time(row: Mapping[str, Any]) -> bool:
            if scope.started_at is None or scope.ended_at is None:
                return False
            for field_name in (
                "occurred_at", "filled_at", "decided_at", "opened_at",
                "created_at", "updated_at",
            ):
                value = row.get(field_name)
                if value is None:
                    continue
                if isinstance(value, str):
                    try:
                        value = datetime.fromisoformat(value)
                    except ValueError:
                        continue
                if isinstance(value, datetime):
                    if value.tzinfo is None:
                        value = value.replace(tzinfo=timezone.utc)
                    return scope.started_at <= value <= scope.ended_at
            return False

        for table in PAPER_TABLES:
            for row in source[table]:
                direct = (
                    (scope.command_id is not None and row.get("command_id") == scope.command_id)
                    or (scope.position_id is not None and row.get("position_id") == scope.position_id)
                    or (scope.symbol is not None and row.get("symbol") == scope.symbol)
                    or in_time(row)
                )
                if direct:
                    selected[table].add(primary(table, row))

        changed = True
        while changed:
            changed = False
            selected_rows = tuple(
                row
                for table in PAPER_TABLES
                for row in source[table]
                if primary(table, row) in selected[table]
            )
            referenced = {
                "paper_execution_commands": {
                    row.get("command_id") for row in selected_rows
                },
                "paper_orders": {
                    value for row in selected_rows
                    for value in (row.get("order_id"), row.get("entry_order_id"))
                },
                "paper_fills": {
                    value for row in selected_rows
                    for value in (row.get("fill_id"), row.get("entry_fill_id"), row.get("exit_fill_id"))
                },
                "paper_positions": {
                    row.get("position_id") for row in selected_rows
                },
                "paper_exit_decisions": {
                    row.get("exit_decision_id") for row in selected_rows
                },
            }
            for table, values in referenced.items():
                existing = {primary(table, row) for row in source[table]}
                additions = (values & existing) - selected[table]
                if additions:
                    selected[table].update(additions)
                    changed = True
            command_ids = selected["paper_execution_commands"]
            order_ids = selected["paper_orders"]
            fill_ids = selected["paper_fills"]
            position_ids = selected["paper_positions"]
            decision_ids = selected["paper_exit_decisions"]
            for table in PAPER_TABLES:
                for row in source[table]:
                    key = primary(table, row)
                    linked = (
                        row.get("command_id") in command_ids
                        or row.get("order_id") in order_ids
                        or row.get("fill_id") in fill_ids
                        or row.get("position_id") in position_ids
                        or row.get("exit_decision_id") in decision_ids
                        or row.get("entry_order_id") in order_ids
                        or row.get("entry_fill_id") in fill_ids
                        or row.get("exit_fill_id") in fill_ids
                    )
                    if linked and key not in selected[table]:
                        selected[table].add(key)
                        changed = True

        return {
            table: tuple(
                row for row in source[table]
                if primary(table, row) in selected[table]
            )
            for table in PAPER_TABLES
        }

    def _evaluate(
        self,
        rows: Mapping[str, Sequence[Mapping[str, Any]]],
        scope: PaperReconciliationScope,
    ) -> tuple[PaperReconciliationFinding, ...]:
        commands = rows["paper_execution_commands"]
        orders = rows["paper_orders"]
        fills = rows["paper_fills"]
        positions = rows["paper_positions"]
        cursors = rows["paper_exit_evaluation_cursors"]
        decisions = rows["paper_exit_decisions"]
        events = rows["paper_order_events"]
        journal = rows["paper_journal_entries"]
        findings: list[PaperReconciliationFinding] = []

        def add(code: str, entity: str, *ids: Any) -> None:
            finding = PaperReconciliationFinding(
                code=code,
                invariant=_INVARIANT[code],
                severity=_SEVERITY[code],
                entity_type=entity,
                safe_ids=_bounded_ids(*ids),
            )
            if finding not in findings:
                findings.append(finding)

        command_ids = {row.get("command_id") for row in commands}
        order_ids = {row.get("order_id") for row in orders}
        fill_ids = {row.get("fill_id") for row in fills}
        position_ids = {row.get("position_id") for row in positions}
        decision_ids = {row.get("exit_decision_id") for row in decisions}

        for value in _duplicates(commands, "idempotency_key"):
            add("COMMAND_SEMANTIC_IDENTITY_DUPLICATE", "command", value)
        for command in commands:
            if command.get("final_paper_approval") is not True:
                add("APPROVAL_LINKAGE_INVALID", "command", command.get("command_id"))
        for value in _duplicates(orders, "idempotency_key"):
            add("DUPLICATE_SEMANTIC_ORDER", "order", value)
        for value in _duplicates(fills, "idempotency_key") | _duplicates(fills, "fill_id"):
            add("DUPLICATE_FILL", "fill", value)

        order_by_id = {row.get("order_id"): row for row in orders}
        fills_by_order: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
        for fill in fills:
            fills_by_order[fill.get("order_id")].append(fill)
            order = order_by_id.get(fill.get("order_id"))
            if order is None:
                add("ORPHAN_FILL", "fill", fill.get("fill_id"), fill.get("order_id"))
            elif fill.get("fill_role") != order.get("order_role"):
                add("FILL_ROLE_MISMATCH", "fill", fill.get("fill_id"), order.get("order_id"))

        events_by_order: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
        for event in events:
            events_by_order[event.get("order_id")].append(event)
            if event.get("order_id") not in order_ids:
                add("ORPHAN_ORDER_EVENT", "order_event", event.get("order_event_id"), event.get("order_id"))
        expected_prefix = ["PAPER_ORDER_CREATED", "PAPER_ORDER_VALIDATED", "PAPER_ORDER_OPENED"]
        for order in orders:
            oid = order.get("order_id")
            ordered = sorted(events_by_order.get(oid, ()), key=lambda row: (row.get("aggregate_version", -1), str(row.get("order_event_id"))))
            types = [row.get("event_type") for row in ordered]
            versions = [row.get("aggregate_version") for row in ordered]
            if types[:3] != expected_prefix:
                add("MISSING_REQUIRED_EVENT", "order", oid)
            if versions != sorted(set(versions)) or any(
                next_row.get("from_state") != current.get("to_state")
                for current, next_row in zip(ordered, ordered[1:])
            ):
                add("INVALID_EVENT_ORDERING", "order", oid)
            if any(b <= a for a, b in zip(versions, versions[1:])):
                add("VERSION_REGRESSION", "order", oid)
            if order.get("state") == "FILLED":
                if len(fills_by_order.get(oid, ())) != 1:
                    add("IMPOSSIBLE_ORDER_POSITION_COMBINATION", "order", oid)
                if "PAPER_ORDER_FILLED" not in types:
                    add("MISSING_REQUIRED_EVENT", "order", oid)
            if order.get("command_id") not in command_ids:
                add("CAUSAL_ID_MISMATCH", "order", oid, order.get("command_id"))

        cursor_by_position: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
        for cursor in cursors:
            pid = cursor.get("position_id")
            cursor_by_position[pid].append(cursor)
            if pid not in position_ids:
                add("ORPHAN_CURSOR", "cursor", cursor.get("cursor_id"), pid)
            if cursor.get("last_evaluated_closed_until_ms", 0) < cursor.get("position_opened_closed_until_ms", 0):
                add("CURSOR_REGRESSION", "cursor", cursor.get("cursor_id"), pid)
            if cursor.get("last_evaluated_closed_until_ms", 0) > self._clock_ms():
                add("FUTURE_CURSOR", "cursor", cursor.get("cursor_id"), pid)
            if cursor.get("version", 0) < 1:
                add("VERSION_REGRESSION", "cursor", cursor.get("cursor_id"), pid)

        decisions_by_position: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
        for decision in decisions:
            pid = decision.get("position_id")
            decisions_by_position[pid].append(decision)
            if pid not in position_ids:
                add("ORPHAN_EXIT_DECISION", "exit_decision", decision.get("exit_decision_id"), pid)

        entry_order_by_fill = {
            fill.get("fill_id"): order_by_id.get(fill.get("order_id")) for fill in fills
        }
        for position in positions:
            pid = position.get("position_id")
            state = position.get("state")
            entry_fill = position.get("entry_fill_id")
            exit_fill = position.get("exit_fill_id")
            if entry_fill not in fill_ids:
                add("OPEN_WITHOUT_ENTRY_FILL", "position", pid, entry_fill)
            entry_order = entry_order_by_fill.get(entry_fill)
            if entry_order is not None and entry_order.get("order_id") != position.get("entry_order_id"):
                add("CAUSAL_ID_MISMATCH", "position", pid, position.get("entry_order_id"))
            if state in {"OPEN", "CLOSING"} and len(cursor_by_position.get(pid, ())) != 1:
                add("OPEN_WITHOUT_CURSOR", "position", pid)
            if state == "CLOSING":
                if not decisions_by_position.get(pid):
                    add("CLOSING_WITHOUT_EXIT_DECISION", "position", pid)
                close_orders = [order for order in orders if order.get("order_role") == "EXIT" and entry_order is not None and order.get("command_id") == entry_order.get("command_id")]
                if not close_orders:
                    add("CLOSING_WITHOUT_CLOSE_ORDER", "position", pid)
            if state == "CLOSED":
                if exit_fill not in fill_ids:
                    add("CLOSED_WITHOUT_CLOSE_FILL", "position", pid, exit_fill)
                if position.get("closed_at") is None:
                    add("IMPOSSIBLE_ORDER_POSITION_COMBINATION", "position", pid)
            elif any(position.get(name) not in (None, 0) for name in ("exit_fill_id", "exit_fees", "realized_pnl")):
                add("FINALIZED_ACCOUNTING_ON_NON_CLOSED_POSITION", "position", pid)

        terminal_by_position: dict[Any, list[Mapping[str, Any]]] = defaultdict(list)
        for item in journal:
            linked = any(
                item.get(field) in valid
                for field, valid in (
                    ("command_id", command_ids),
                    ("order_id", order_ids),
                    ("fill_id", fill_ids),
                    ("position_id", position_ids),
                    ("exit_decision_id", decision_ids),
                )
            )
            if not linked:
                add("ORPHAN_JOURNAL", "journal", item.get("journal_entry_id"))
            if item.get("event_type") == "PAPER_POSITION_CLOSED":
                terminal_by_position[item.get("position_id")].append(item)
        for pid, items in terminal_by_position.items():
            if len(items) > 1:
                add("DUPLICATE_TERMINAL_JOURNAL_ACCOUNTING", "position", pid)
                add("DOUBLE_FEE", "position", pid)
                add("DOUBLE_PNL", "position", pid)

        for position in positions:
            pid = position.get("position_id")
            if position.get("state") == "CLOSED" and len(terminal_by_position.get(pid, ())) != 1:
                add("MISSING_REQUIRED_EVENT", "position", pid)

        for decision in decisions:
            pid = decision.get("position_id")
            related_journal = [item for item in journal if item.get("exit_decision_id") == decision.get("exit_decision_id")]
            related_order_ids = {item.get("order_id") for item in related_journal if item.get("order_id")}
            for oid in related_order_ids:
                order = order_by_id.get(oid)
                if order is not None and order.get("order_role") != "EXIT":
                    add("WRONG_CLOSE_LINEAGE", "exit_decision", decision.get("exit_decision_id"), oid, pid)

        return tuple(sorted(findings, key=lambda item: (item.code, item.entity_type, item.safe_ids)))


def safe_report(result: PaperReconciliationResult) -> str:
    payload = {
        "schema_version": PAPER_RECONCILIATION_SCHEMA_VERSION,
        "request_id": result.request_id,
        "target_class": result.target_class,
        "schema_head": result.schema_head,
        "scope": result.scope.safe_summary(),
        "outcome": result.outcome.value,
        "entity_counts": asdict(result.entity_summary),
        "severity_counts": result.severity_counts,
        "finding_codes": [finding.code for finding in result.findings],
        "safe_ids": sorted({safe_id for finding in result.findings for safe_id in finding.safe_ids})[:32],
        "read_only": result.read_only,
        "query_count": result.query_count,
        "paper_table_queries": result.paper_table_queries,
        "duration_ms": result.duration_ms,
        "correlation_id": result.correlation_id,
        "reason_code": result.reason_code,
    }
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    if len(rendered.encode("utf-8")) > MAX_SAFE_REPORT_BYTES:
        raise ValueError("SAFE_REPORT_SIZE_LIMIT_EXCEEDED")
    return rendered


@dataclass(frozen=True, slots=True)
class PaperReconciliationSafeTargetManifest:
    target_class: str
    target_identity: str
    expected_schema_head: str

    def __post_init__(self) -> None:
        for value in (self.target_class, self.target_identity, self.expected_schema_head):
            _safe_id(value, required=True)
        if self.expected_schema_head != EXPECTED_SCHEMA_HEAD:
            raise ValueError("UNSUPPORTED_EXPECTED_SCHEMA_HEAD")


def load_safe_target_manifest(path: Path) -> PaperReconciliationSafeTargetManifest:
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, dict) or set(source) != {
        "target_class", "target_identity", "expected_schema_head"
    }:
        raise ValueError("TARGET_MANIFEST_FIELDS_REJECTED")
    forbidden = ("uri", "dsn", "password", "credential", "environment", "binding", "path")
    serialized_keys = " ".join(str(key).lower() for key in source)
    if any(token in serialized_keys for token in forbidden):
        raise ValueError("TARGET_MANIFEST_SECRET_FIELD_REJECTED")
    return PaperReconciliationSafeTargetManifest(**source)


def main(
    argv: Sequence[str] | None = None,
    *,
    reader_factory: Callable[[PaperReconciliationRequest], PaperReconciliationReader]
    | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.engine_paper.reconciliation")
    parser.add_argument("--target", required=True)
    parser.add_argument("--read-only-reconcile", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = load_safe_target_manifest(Path(args.target))
        request = PaperReconciliationRequest(
            request_id="cli-request",
            correlation_id="cli-correlation",
            target_class=manifest.target_class,
            target_identity=manifest.target_identity,
            expected_schema_head=manifest.expected_schema_head,
            scope=PaperReconciliationScope(),
        )
        if reader_factory is not None:
            result = PaperReadOnlyReconciliationService(reader_factory).reconcile(
                request
            )
        else:
            result = PaperReconciliationResult(
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                target_class=request.target_class,
                schema_head=None,
                scope=request.scope,
                outcome=PaperReconciliationOutcome.TARGET_REJECTED,
                entity_summary=PaperReconciliationEntitySummary(),
                findings=(),
                read_only=True,
                query_count=0,
                paper_table_queries=0,
                business_mutations=0,
                schema_mutations=0,
                duration_ms=0,
                reason_code="NO_PERMANENT_SAFE_TARGET_RESOLVER_CONFIGURED",
            )
    except Exception:
        result = PaperReconciliationResult(
            request_id="cli-request",
            correlation_id="cli-correlation",
            target_class="REJECTED",
            schema_head=None,
            scope=PaperReconciliationScope(),
            outcome=PaperReconciliationOutcome.TARGET_REJECTED,
            entity_summary=PaperReconciliationEntitySummary(),
            findings=(),
            read_only=True,
            query_count=0,
            paper_table_queries=0,
            business_mutations=0,
            schema_mutations=0,
            duration_ms=0,
            reason_code="TARGET_MANIFEST_REJECTED",
        )
    print(safe_report(result))
    return int(result.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if name.startswith("Paper") or name in {"safe_report", "main"}]
