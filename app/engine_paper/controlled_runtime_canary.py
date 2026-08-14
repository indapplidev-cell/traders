"""One-shot, isolated-only mutating canary for the controlled PAPER worker.

The boundary is deliberately caller-driven: one request, one read-only dry
run, at most one worker invocation, at most one committed child stage, a fresh
postflight read, and return.  It owns no business transaction and contains no
polling, retry, scheduler, daemon, network, or production-target path.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
import re
from threading import Lock
from typing import Final, Protocol

from sqlalchemy import text

from app.engine_paper.controlled_runtime import (
    PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION,
    PaperControlledRuntimeAction,
    PaperControlledRuntimeAvailableInputSummary,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeDryRunRequest,
    PaperControlledRuntimeDryRunResult,
    PaperControlledRuntimeDryRunService,
    PaperControlledRuntimeOutcome,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
    PaperGraphConsistencyStatus,
    evaluate_controlled_runtime_startup_gate,
)
from app.engine_paper.controlled_worker import (
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleOutcome,
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleResult,
    PaperLifecycleCycleScope,
    PaperLifecycleGraph,
    PaperLifecycleStage,
    PaperLifecycleState,
    classify_paper_lifecycle_state,
)
from app.engine_safety import ExecutionMode
from app.engine_safety.paper_domain import require_identity, require_utc


TASK_ID: Final = (
    "TRADERS_ML_PAPER_TRADING_CONTROLLED_RUNTIME_SINGLE_CYCLE_CANARY_01_RETRY_02"
)
PAPER_CONTROLLED_RUNTIME_CANARY_CONTRACT_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_SINGLE_CYCLE_CANARY_V1"
)
PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_V1"
)
PAPER_CONTROLLED_RUNTIME_CANARY_TARGET_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_CANARY_TARGET_V1"
)
CANARY_ACKNOWLEDGEMENT: Final = "I_ACKNOWLEDGE_ONE_ISOLATED_PAPER_STAGE"
EXPECTED_MIGRATION_HEAD: Final = (
    "0015_trading_universe_activation"
)
MAX_SAFE_RESULT_IDENTITIES: Final = 16
MAX_SAFE_REASON_LENGTH: Final = 96
_SAFE_DATABASE_RE: Final = re.compile(r"paper_test_[a-z0-9_]{1,48}\Z")
_SAFE_ROLE_RE: Final = re.compile(r"paper_canary_[a-z0-9_]{1,48}\Z")
_FORBIDDEN_NAME_PARTS: Final = (
    "production",
    "prod_",
    "_prod",
    "readonly",
    "shared",
    "traders_ml",
)


class PaperControlledRuntimeCanaryStage(StrEnum):
    INGEST_COMMAND = "INGEST_COMMAND"
    EXECUTE_ENTRY = "EXECUTE_ENTRY"
    EVALUATE_EXIT_NO_TRIGGER = "EVALUATE_EXIT_NO_TRIGGER"
    EVALUATE_EXIT_TRIGGER = "EVALUATE_EXIT_TRIGGER"
    EXECUTE_CLOSE = "EXECUTE_CLOSE"


class PaperControlledRuntimeCanaryOutcome(StrEnum):
    CANARY_STAGE_COMPLETED = "CANARY_STAGE_COMPLETED"
    CANARY_ALREADY_ADVANCED = "CANARY_ALREADY_ADVANCED"
    CANARY_STAGE_IDEMPOTENT_EXISTING = "CANARY_STAGE_IDEMPOTENT_EXISTING"
    CANARY_CONFIGURATION_INVALID = "CANARY_CONFIGURATION_INVALID"
    CANARY_TARGET_FORBIDDEN = "CANARY_TARGET_FORBIDDEN"
    CANARY_TARGET_IDENTITY_MISMATCH = "CANARY_TARGET_IDENTITY_MISMATCH"
    CANARY_MIGRATION_HEAD_MISMATCH = "CANARY_MIGRATION_HEAD_MISMATCH"
    CANARY_PAPER_AUTHORIZATION_MISSING = "CANARY_PAPER_AUTHORIZATION_MISSING"
    CANARY_LIVE_FORBIDDEN = "CANARY_LIVE_FORBIDDEN"
    CANARY_SCOPE_INVALID = "CANARY_SCOPE_INVALID"
    CANARY_STAGE_LIMIT_INVALID = "CANARY_STAGE_LIMIT_INVALID"
    CANARY_NETWORK_FORBIDDEN = "CANARY_NETWORK_FORBIDDEN"
    CANARY_POLLING_FORBIDDEN = "CANARY_POLLING_FORBIDDEN"
    CANARY_SCHEDULER_FORBIDDEN = "CANARY_SCHEDULER_FORBIDDEN"
    CANARY_DAEMON_FORBIDDEN = "CANARY_DAEMON_FORBIDDEN"
    CANARY_SYMBOL_NOT_ALLOWED = "CANARY_SYMBOL_NOT_ALLOWED"
    CANARY_GRAPH_INCONSISTENT = "CANARY_GRAPH_INCONSISTENT"
    CANARY_EXPECTED_VERSION_STALE = "CANARY_EXPECTED_VERSION_STALE"
    CANARY_DRY_RUN_NOT_READY = "CANARY_DRY_RUN_NOT_READY"
    CANARY_STAGE_MISMATCH = "CANARY_STAGE_MISMATCH"
    CANARY_GRAPH_CHANGED_AFTER_DRY_RUN = "CANARY_GRAPH_CHANGED_AFTER_DRY_RUN"
    CANARY_ARMING_INVALID = "CANARY_ARMING_INVALID"
    CANARY_ARMING_EXPIRED = "CANARY_ARMING_EXPIRED"
    CANARY_CANCELLED_BEFORE_MUTATION = "CANARY_CANCELLED_BEFORE_MUTATION"
    CANARY_CHILD_STAGE_FAILED = "CANARY_CHILD_STAGE_FAILED"
    CANARY_CHILD_OUTCOME_UNEXPECTED = "CANARY_CHILD_OUTCOME_UNEXPECTED"
    CANARY_POSTFLIGHT_GRAPH_INCONSISTENT = (
        "CANARY_POSTFLIGHT_GRAPH_INCONSISTENT"
    )
    CANARY_MUTATION_BUDGET_EXCEEDED = "CANARY_MUTATION_BUDGET_EXCEEDED"
    CANARY_CANCELLED_AFTER_COMMITTED_STAGE = (
        "CANARY_CANCELLED_AFTER_COMMITTED_STAGE"
    )
    CANARY_POSTFLIGHT_READ_FAILED = "CANARY_POSTFLIGHT_READ_FAILED"
    CANARY_EXPLICIT_ACKNOWLEDGEMENT_MISSING = (
        "CANARY_EXPLICIT_ACKNOWLEDGEMENT_MISSING"
    )


class PaperControlledRuntimeCanaryFaultPoint(StrEnum):
    BEFORE_CONFIGURATION_VALIDATION = "BEFORE_CONFIGURATION_VALIDATION"
    AFTER_CONFIGURATION_VALIDATION = "AFTER_CONFIGURATION_VALIDATION"
    BEFORE_ISOLATED_TARGET_VALIDATION = "BEFORE_ISOLATED_TARGET_VALIDATION"
    AFTER_TARGET_VALIDATION = "AFTER_TARGET_VALIDATION"
    BEFORE_DRY_RUN = "BEFORE_DRY_RUN"
    AFTER_DRY_RUN = "AFTER_DRY_RUN"
    BEFORE_FINGERPRINT_CHECK = "BEFORE_FINGERPRINT_CHECK"
    AFTER_FINGERPRINT_CHECK = "AFTER_FINGERPRINT_CHECK"
    BEFORE_WORKER_INVOCATION = "BEFORE_WORKER_INVOCATION"
    AFTER_WORKER_RETURN_BEFORE_POSTFLIGHT = (
        "AFTER_WORKER_RETURN_BEFORE_POSTFLIGHT"
    )
    DURING_POSTFLIGHT_READ = "DURING_POSTFLIGHT_READ"
    AFTER_POSTFLIGHT_BEFORE_RESULT = "AFTER_POSTFLIGHT_BEFORE_RESULT"


class PaperControlledRuntimeCanaryCancellationAuthority(Protocol):
    def is_cancelled(self) -> bool: ...


class PaperControlledRuntimeCanaryGraphLoader(Protocol):
    def load(self, command_id: str) -> PaperLifecycleGraph: ...


class PaperControlledRuntimeCanaryTargetValidatorProtocol(Protocol):
    def validate(
        self, identity: "PaperControlledRuntimeCanaryTargetIdentity"
    ) -> "PaperControlledRuntimeCanaryTargetValidation": ...


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeCanaryTargetIdentity:
    target_kind: object
    task_id: str
    canary_run_id: str
    database_name: str
    database_role_name: str
    migration_head: str
    ownership_marker: str
    created_at: datetime
    expires_at: datetime
    contract_version: str = PAPER_CONTROLLED_RUNTIME_CANARY_TARGET_VERSION

    def __post_init__(self) -> None:
        for name in (
            "task_id",
            "canary_run_id",
            "database_name",
            "database_role_name",
            "migration_head",
            "ownership_marker",
            "contract_version",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        require_utc(self.created_at, "created_at")
        require_utc(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeCanaryTargetValidation:
    valid: bool
    outcome: PaperControlledRuntimeCanaryOutcome
    migration_head: str | None = None
    database_name: str | None = None
    database_role_name: str | None = None


class SqlAlchemyPaperControlledRuntimeCanaryTargetValidator:
    """Read only three allowlisted non-secret PostgreSQL identity fields."""

    def __init__(self, session_factory: Callable) -> None:
        self._session_factory = session_factory

    def validate(
        self, identity: PaperControlledRuntimeCanaryTargetIdentity
    ) -> PaperControlledRuntimeCanaryTargetValidation:
        if not valid_canary_target_identity(identity):
            return PaperControlledRuntimeCanaryTargetValidation(
                False,
                PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_IDENTITY_MISMATCH,
            )
        session = self._session_factory()
        try:
            transaction = session.begin()
            session.execute(text("SET TRANSACTION READ ONLY"))
            database_name, role_name = session.execute(
                text("SELECT current_database(), current_user")
            ).one()
            migration_head = session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            transaction.rollback()
        except Exception:
            session.rollback()
            return PaperControlledRuntimeCanaryTargetValidation(
                False,
                PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_IDENTITY_MISMATCH,
            )
        finally:
            session.close()
        if migration_head != identity.migration_head:
            return PaperControlledRuntimeCanaryTargetValidation(
                False,
                PaperControlledRuntimeCanaryOutcome.CANARY_MIGRATION_HEAD_MISMATCH,
                str(migration_head)[:MAX_SAFE_REASON_LENGTH]
                if migration_head is not None
                else None,
                str(database_name)[:64],
                str(role_name)[:64],
            )
        valid = (
            database_name == identity.database_name
            and role_name == identity.database_role_name
        )
        return PaperControlledRuntimeCanaryTargetValidation(
            valid,
            (
                PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED
                if valid
                else PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_IDENTITY_MISMATCH
            ),
            str(migration_head)[:MAX_SAFE_REASON_LENGTH],
            str(database_name)[:64],
            str(role_name)[:64],
        )


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeCanaryMutationBudget:
    stage: PaperControlledRuntimeCanaryStage
    command_inserts: int = 0
    order_inserts: int = 0
    order_updates: int = 0
    fill_inserts: int = 0
    position_inserts: int = 0
    position_updates: int = 0
    cursor_inserts: int = 0
    cursor_updates: int = 0
    exit_decision_inserts: int = 0
    order_event_inserts: int = 0
    journal_inserts: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.stage, PaperControlledRuntimeCanaryStage):
            raise TypeError("stage must be a canary stage")
        for item in fields(self):
            if item.name == "stage":
                continue
            value = getattr(self, item.name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{item.name} must be a non-negative integer")

    @classmethod
    def exact_for_stage(
        cls, stage: PaperControlledRuntimeCanaryStage
    ) -> "PaperControlledRuntimeCanaryMutationBudget":
        values = {
            PaperControlledRuntimeCanaryStage.INGEST_COMMAND: dict(
                command_inserts=1,
                order_inserts=1,
                order_event_inserts=3,
                journal_inserts=4,
            ),
            PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY: dict(
                order_updates=1,
                fill_inserts=1,
                position_inserts=1,
                cursor_inserts=1,
                order_event_inserts=1,
                journal_inserts=2,
            ),
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER: dict(
                cursor_updates=1,
            ),
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER: dict(
                order_inserts=1,
                position_updates=1,
                cursor_updates=1,
                exit_decision_inserts=1,
                order_event_inserts=3,
                journal_inserts=4,
            ),
            PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE: dict(
                order_updates=1,
                fill_inserts=1,
                position_updates=1,
                order_event_inserts=1,
                journal_inserts=2,
            ),
        }[stage]
        return cls(stage=stage, **values)


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeCanaryRowCountDeltas:
    command_inserts: int = 0
    order_inserts: int = 0
    order_updates: int = 0
    fill_inserts: int = 0
    position_inserts: int = 0
    position_updates: int = 0
    cursor_inserts: int = 0
    cursor_updates: int = 0
    exit_decision_inserts: int = 0
    order_event_inserts: int = 0
    journal_inserts: int = 0


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeCanaryEntitySummary:
    entity_kind: str
    entity_id: str
    state: str | None
    version: int | None


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeCanaryArming:
    arming_contract_version: str
    task_id: str
    canary_run_id: str
    configuration_id: str
    target_identity: PaperControlledRuntimeCanaryTargetIdentity
    expected_stage: PaperControlledRuntimeCanaryStage
    expected_graph_fingerprint: str
    expires_at: datetime
    single_use: bool
    explicit_acknowledgement: str

    def __post_init__(self) -> None:
        for name in (
            "arming_contract_version",
            "task_id",
            "canary_run_id",
            "configuration_id",
            "expected_graph_fingerprint",
            "explicit_acknowledgement",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        require_utc(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeSingleCycleCanaryRequest:
    request_id: str
    task_id: str
    canary_run_id: str
    configuration: PaperControlledRuntimeConfiguration
    target_identity: PaperControlledRuntimeCanaryTargetIdentity
    arming: PaperControlledRuntimeCanaryArming
    cycle_request: PaperLifecycleCycleRequest
    expected_initial_state: PaperLifecycleState
    expected_stage: PaperControlledRuntimeCanaryStage
    expected_graph_fingerprint: str
    expected_mutation_budget: PaperControlledRuntimeCanaryMutationBudget
    created_at: datetime
    evaluated_at: datetime
    correlation_id: str
    symbol: str
    cancellation_authority: (
        PaperControlledRuntimeCanaryCancellationAuthority | None
    ) = None
    contract_version: str = PAPER_CONTROLLED_RUNTIME_CANARY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "request_id",
            "task_id",
            "canary_run_id",
            "expected_graph_fingerprint",
            "correlation_id",
            "contract_version",
        ):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        object.__setattr__(self, "symbol", str(self.symbol).strip().upper())
        require_utc(self.created_at, "created_at")
        require_utc(self.evaluated_at, "evaluated_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeSingleCycleCanaryResult:
    request_id: str
    canary_run_id: str
    outcome: PaperControlledRuntimeCanaryOutcome
    reason_code: str
    configuration_outcome: str
    startup_gate_outcome: str
    preflight_outcome: str
    dry_run_outcome: str
    initial_lifecycle_state: PaperLifecycleState | None
    expected_stage: PaperControlledRuntimeCanaryStage
    actual_attempted_stage: PaperControlledRuntimeCanaryStage | None
    worker_outcome: str | None
    child_outcome: str | None
    child_reason: str | None
    postflight_lifecycle_state: PaperLifecycleState | None
    mutation_budget_result: str
    row_count_deltas: PaperControlledRuntimeCanaryRowCountDeltas
    entity_summary: tuple[PaperControlledRuntimeCanaryEntitySummary, ...]
    worker_invocations: int
    mutating_stage_invocations: int
    cancellation_outcome: str
    cleanup_outcome: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class _GraphSnapshot:
    counts: tuple[int, int, int, int, int, int, int, int]
    versions: tuple[tuple[str, int | None], ...]


def canary_ownership_marker(
    task_id: str, canary_run_id: str, database_name: str, database_role_name: str
) -> str:
    material = "\x1f".join(
        (task_id, canary_run_id, database_name, database_role_name)
    ).encode("utf-8")
    return f"paper-canary-owner:{sha256(material).hexdigest()[:32]}"


def valid_canary_target_identity(
    identity: PaperControlledRuntimeCanaryTargetIdentity,
) -> bool:
    if not isinstance(identity, PaperControlledRuntimeCanaryTargetIdentity):
        return False
    names = (identity.database_name.lower(), identity.database_role_name.lower())
    return (
        identity.contract_version == PAPER_CONTROLLED_RUNTIME_CANARY_TARGET_VERSION
        and identity.target_kind is PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL
        and identity.task_id == TASK_ID
        and _SAFE_DATABASE_RE.fullmatch(identity.database_name) is not None
        and _SAFE_ROLE_RE.fullmatch(identity.database_role_name) is not None
        and not any(part in name for name in names for part in _FORBIDDEN_NAME_PARTS)
        and identity.migration_head == EXPECTED_MIGRATION_HEAD
        and identity.ownership_marker
        == canary_ownership_marker(
            identity.task_id,
            identity.canary_run_id,
            identity.database_name,
            identity.database_role_name,
        )
        and identity.created_at < identity.expires_at
    )


def _safe_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    return value


def _material(entity: object, id_name: str) -> dict[str, object]:
    result: dict[str, object] = {"id": getattr(entity, id_name)}
    for name in ("state", "version", "symbol", "mode"):
        if hasattr(entity, name):
            result[name] = _safe_value(getattr(entity, name))
    return result


def paper_canary_graph_fingerprint(
    graph: PaperLifecycleGraph,
    expected_stage: PaperControlledRuntimeCanaryStage,
) -> str:
    """Hash only explicit, bounded, non-secret material lifecycle identity."""

    command = graph.command
    payload = {
        "command": _material(command, "command_id") if command is not None else None,
        "orders": sorted(
            (
                {"role": node.role, **_material(node.order, "order_id")}
                for node in graph.orders
            ),
            key=lambda item: (str(item["role"]), str(item["id"])),
        ),
        "fills": sorted(
            (_material(item, "fill_id") for item in graph.fills),
            key=lambda item: str(item["id"]),
        ),
        "positions": sorted(
            (_material(item, "position_id") for item in graph.positions),
            key=lambda item: str(item["id"]),
        ),
        "cursors": sorted(
            (_material(item, "cursor_id") for item in graph.cursors),
            key=lambda item: str(item["id"]),
        ),
        "exit_decisions": sorted(
            (_material(item, "exit_decision_id") for item in graph.exit_decisions),
            key=lambda item: str(item["id"]),
        ),
        "expected_stage": expected_stage.value,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return sha256(encoded).hexdigest()


def _worker_stage(stage: PaperControlledRuntimeCanaryStage) -> PaperLifecycleStage:
    if stage in {
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER,
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER,
    }:
        return PaperLifecycleStage.EVALUATE_EXIT
    return PaperLifecycleStage(stage.value)


def _snapshot(graph: PaperLifecycleGraph) -> _GraphSnapshot:
    versions: list[tuple[str, int | None]] = []
    if graph.command is not None:
        versions.append(
            (
                f"command:{graph.command.command_id}",
                getattr(graph.command, "version", None),
            )
        )
    versions.extend(
        (f"order:{node.order.order_id}", node.order.version) for node in graph.orders
    )
    versions.extend(
        (f"position:{item.position_id}", item.version) for item in graph.positions
    )
    versions.extend((f"cursor:{item.cursor_id}", item.version) for item in graph.cursors)
    return _GraphSnapshot(
        counts=(
            int(graph.command is not None),
            len(graph.orders),
            len(graph.fills),
            len(graph.positions),
            len(graph.cursors),
            len(graph.exit_decisions),
            len(graph.order_events),
            len(graph.journal),
        ),
        versions=tuple(sorted(versions)),
    )


def _deltas(before: _GraphSnapshot, after: _GraphSnapshot) -> PaperControlledRuntimeCanaryRowCountDeltas:
    count_deltas = tuple(a - b for b, a in zip(before.counts, after.counts))
    before_versions = dict(before.versions)
    after_versions = dict(after.versions)

    def updates(prefix: str) -> int:
        return sum(
            1
            for identity, version in after_versions.items()
            if identity.startswith(prefix)
            and identity in before_versions
            and before_versions[identity] != version
        )

    return PaperControlledRuntimeCanaryRowCountDeltas(
        command_inserts=count_deltas[0],
        order_inserts=count_deltas[1],
        order_updates=updates("order:"),
        fill_inserts=count_deltas[2],
        position_inserts=count_deltas[3],
        position_updates=updates("position:"),
        cursor_inserts=count_deltas[4],
        cursor_updates=updates("cursor:"),
        exit_decision_inserts=count_deltas[5],
        order_event_inserts=count_deltas[6],
        journal_inserts=count_deltas[7],
    )


def mutation_budget_matches(
    budget: PaperControlledRuntimeCanaryMutationBudget,
    deltas: PaperControlledRuntimeCanaryRowCountDeltas,
) -> bool:
    return all(
        getattr(budget, item.name) == getattr(deltas, item.name)
        for item in fields(deltas)
    )


def _entity_summary(
    graph: PaperLifecycleGraph,
) -> tuple[PaperControlledRuntimeCanaryEntitySummary, ...]:
    values: list[PaperControlledRuntimeCanaryEntitySummary] = []

    def add(kind: str, entity: object, id_name: str) -> None:
        state = getattr(entity, "state", None)
        values.append(
            PaperControlledRuntimeCanaryEntitySummary(
                kind,
                str(getattr(entity, id_name))[:96],
                str(_safe_value(state))[:48] if state is not None else None,
                getattr(entity, "version", None),
            )
        )

    if graph.command is not None:
        add("COMMAND", graph.command, "command_id")
    for node in graph.orders:
        add(f"ORDER_{node.role}", node.order, "order_id")
    for entity, kind, id_name in (
        *((item, "FILL", "fill_id") for item in graph.fills),
        *((item, "POSITION", "position_id") for item in graph.positions),
        *((item, "CURSOR", "cursor_id") for item in graph.cursors),
        *((item, "EXIT_DECISION", "exit_decision_id") for item in graph.exit_decisions),
    ):
        add(kind, entity, id_name)
    return tuple(values[:MAX_SAFE_RESULT_IDENTITIES])


def _canary_configuration_outcome(
    configuration: PaperControlledRuntimeConfiguration,
) -> PaperControlledRuntimeCanaryOutcome | None:
    if not isinstance(configuration, PaperControlledRuntimeConfiguration):
        return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
    if configuration.target is not PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL:
        return PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_FORBIDDEN
    if configuration.execution_mode is ExecutionMode.LIVE:
        return PaperControlledRuntimeCanaryOutcome.CANARY_LIVE_FORBIDDEN
    if configuration.execution_mode is not ExecutionMode.PAPER:
        return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
    if configuration.explicit_paper_authorization is not True:
        return PaperControlledRuntimeCanaryOutcome.CANARY_PAPER_AUTHORIZATION_MISSING
    if configuration.runtime_action is not PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY:
        return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
    if configuration.cycle_scope is not PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP:
        return PaperControlledRuntimeCanaryOutcome.CANARY_SCOPE_INVALID
    if configuration.max_stages_per_cycle != 1:
        return PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_LIMIT_INVALID
    if configuration.database_access_mode is not PaperDatabaseAccessMode.ISOLATED_CANARY_READ_WRITE:
        return PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_FORBIDDEN
    if not configuration.runtime_enabled or not configuration.dry_run_enabled:
        return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
    if configuration.network_access_allowed:
        return PaperControlledRuntimeCanaryOutcome.CANARY_NETWORK_FORBIDDEN
    if configuration.polling_allowed:
        return PaperControlledRuntimeCanaryOutcome.CANARY_POLLING_FORBIDDEN
    if configuration.scheduler_allowed:
        return PaperControlledRuntimeCanaryOutcome.CANARY_SCHEDULER_FORBIDDEN
    if configuration.daemon_allowed:
        return PaperControlledRuntimeCanaryOutcome.CANARY_DAEMON_FORBIDDEN
    gate = evaluate_controlled_runtime_startup_gate(configuration)
    if not gate.ready:
        return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
    return None


class PaperControlledRuntimeSingleCycleCanaryService:
    """Deterministic service-level one-shot invocation harness."""

    def __init__(
        self,
        *,
        graph_loader: PaperControlledRuntimeCanaryGraphLoader,
        dry_run_service: PaperControlledRuntimeDryRunService,
        worker: PaperControlledLifecycleWorker,
        target_validator: PaperControlledRuntimeCanaryTargetValidatorProtocol,
        fault_injector: (
            Callable[[PaperControlledRuntimeCanaryFaultPoint], None] | None
        ) = None,
    ) -> None:
        self._graph_loader = graph_loader
        self._dry_run_service = dry_run_service
        self._worker = worker
        self._target_validator = target_validator
        self._fault_injector = fault_injector
        self._invocation_lock = Lock()

    def run(
        self, request: PaperControlledRuntimeSingleCycleCanaryRequest
    ) -> PaperControlledRuntimeSingleCycleCanaryResult:
        if not isinstance(request, PaperControlledRuntimeSingleCycleCanaryRequest):
            raise TypeError("request must be a single-cycle canary request")
        with self._invocation_lock:
            return self._run_locked(request)

    def _run_locked(
        self, request: PaperControlledRuntimeSingleCycleCanaryRequest
    ) -> PaperControlledRuntimeSingleCycleCanaryResult:
        worker_invocations = 0
        before_graph: PaperLifecycleGraph | None = None
        worker_result: PaperLifecycleCycleResult | None = None
        dry_result: PaperControlledRuntimeDryRunResult | None = None
        try:
            self._fault(PaperControlledRuntimeCanaryFaultPoint.BEFORE_CONFIGURATION_VALIDATION)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID,
            )
        configuration_failure = _canary_configuration_outcome(request.configuration)
        request_failure = self._validate_request(request)
        if configuration_failure is not None or request_failure is not None:
            return self._failure(request, configuration_failure or request_failure)
        try:
            self._fault(PaperControlledRuntimeCanaryFaultPoint.AFTER_CONFIGURATION_VALIDATION)
            if self._cancelled(request):
                return self._failure(
                    request,
                    PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_BEFORE_MUTATION,
                    cancellation="CANCELLED_BEFORE_MUTATION",
                )
            self._fault(PaperControlledRuntimeCanaryFaultPoint.BEFORE_ISOLATED_TARGET_VALIDATION)
            target = self._target_validator.validate(request.target_identity)
            if not target.valid:
                return self._failure(request, target.outcome)
            self._fault(PaperControlledRuntimeCanaryFaultPoint.AFTER_TARGET_VALIDATION)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_IDENTITY_MISMATCH,
            )
        if self._cancelled(request):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_BEFORE_MUTATION,
                cancellation="CANCELLED_BEFORE_MUTATION",
            )
        try:
            dry_run_source_graph = self._graph_loader.load(
                request.cycle_request.command_id
            )
            dry_run_source_state = classify_paper_lifecycle_state(
                dry_run_source_graph
            )
            dry_run_source_fingerprint = paper_canary_graph_fingerprint(
                dry_run_source_graph, request.expected_stage
            )
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_DRY_RUN_NOT_READY,
            )
        if dry_run_source_state is PaperLifecycleState.INCONSISTENT:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_GRAPH_INCONSISTENT,
            )
        if (
            dry_run_source_state is not request.expected_initial_state
            or dry_run_source_fingerprint != request.expected_graph_fingerprint
        ):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_ALREADY_ADVANCED,
            )
        try:
            self._fault(PaperControlledRuntimeCanaryFaultPoint.BEFORE_DRY_RUN)
            dry_result = self._dry_run_service.plan(self._dry_run_request(request))
            self._fault(PaperControlledRuntimeCanaryFaultPoint.AFTER_DRY_RUN)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_DRY_RUN_NOT_READY,
            )
        if (
            dry_result.dry_run_status
            is not PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY
        ):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_DRY_RUN_NOT_READY,
                dry_result=dry_result,
            )
        expected_worker_stage = _worker_stage(request.expected_stage)
        if dry_result.next_eligible_stage is not expected_worker_stage:
            outcome = (
                PaperControlledRuntimeCanaryOutcome.CANARY_ALREADY_ADVANCED
                if dry_result.initial_lifecycle_state
                is not request.expected_initial_state
                else PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_MISMATCH
            )
            return self._failure(request, outcome, dry_result=dry_result)
        if self._cancelled(request):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_BEFORE_MUTATION,
                dry_result=dry_result,
                cancellation="CANCELLED_BEFORE_MUTATION",
            )
        if self._cancelled(request):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_BEFORE_MUTATION,
                dry_result=dry_result,
                cancellation="CANCELLED_BEFORE_MUTATION",
            )
        arming_failure = self._validate_arming(request)
        if arming_failure is not None:
            return self._failure(request, arming_failure, dry_result=dry_result)
        try:
            self._fault(PaperControlledRuntimeCanaryFaultPoint.BEFORE_FINGERPRINT_CHECK)
            before_graph = self._graph_loader.load(request.cycle_request.command_id)
            before_state = classify_paper_lifecycle_state(before_graph)
            fingerprint = paper_canary_graph_fingerprint(
                before_graph, request.expected_stage
            )
            if before_state is PaperLifecycleState.INCONSISTENT:
                return self._failure(
                    request,
                    PaperControlledRuntimeCanaryOutcome.CANARY_GRAPH_INCONSISTENT,
                    dry_result=dry_result,
                )
            if (
                before_state is not dry_run_source_state
                or fingerprint != dry_run_source_fingerprint
            ):
                return self._failure(
                    request,
                    PaperControlledRuntimeCanaryOutcome.CANARY_GRAPH_CHANGED_AFTER_DRY_RUN,
                    dry_result=dry_result,
                )
            self._fault(PaperControlledRuntimeCanaryFaultPoint.AFTER_FINGERPRINT_CHECK)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_GRAPH_CHANGED_AFTER_DRY_RUN,
                dry_result=dry_result,
            )
        if self._cancelled(request):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_BEFORE_MUTATION,
                dry_result=dry_result,
                cancellation="CANCELLED_BEFORE_MUTATION",
            )
        try:
            self._fault(PaperControlledRuntimeCanaryFaultPoint.BEFORE_WORKER_INVOCATION)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CHILD_STAGE_FAILED,
                dry_result=dry_result,
            )
        worker_invocations = 1
        worker_result = self._worker.run_cycle(request.cycle_request)
        try:
            self._fault(
                PaperControlledRuntimeCanaryFaultPoint.AFTER_WORKER_RETURN_BEFORE_POSTFLIGHT
            )
            self._fault(PaperControlledRuntimeCanaryFaultPoint.DURING_POSTFLIGHT_READ)
            after_graph = self._graph_loader.load(request.cycle_request.command_id)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_POSTFLIGHT_READ_FAILED,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                cancellation=(
                    "CANCELLED_AFTER_COMMITTED_STAGE"
                    if self._cancelled(request)
                    else "NOT_CANCELLED"
                ),
            )
        after_state = classify_paper_lifecycle_state(after_graph)
        deltas = _deltas(_snapshot(before_graph), _snapshot(after_graph))
        expected_outcome = worker_result.outcome in {
            PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED,
            PaperLifecycleCycleOutcome.CYCLE_COMPLETE,
        }
        if not expected_outcome or worker_result.stages_attempted != 1:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CHILD_STAGE_FAILED,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                after_graph=after_graph,
                deltas=deltas,
            )
        if worker_result.stages_completed > 1:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CHILD_OUTCOME_UNEXPECTED,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                after_graph=after_graph,
                deltas=deltas,
            )
        if after_state is PaperLifecycleState.INCONSISTENT:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_POSTFLIGHT_GRAPH_INCONSISTENT,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                after_graph=after_graph,
                deltas=deltas,
            )
        if not mutation_budget_matches(request.expected_mutation_budget, deltas):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_MUTATION_BUDGET_EXCEEDED,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                after_graph=after_graph,
                deltas=deltas,
            )
        if not self._exit_stage_outcome_matches(request.expected_stage, worker_result):
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_CHILD_OUTCOME_UNEXPECTED,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                after_graph=after_graph,
                deltas=deltas,
            )
        cancelled_after = self._cancelled(request)
        try:
            self._fault(PaperControlledRuntimeCanaryFaultPoint.AFTER_POSTFLIGHT_BEFORE_RESULT)
        except Exception:
            return self._failure(
                request,
                PaperControlledRuntimeCanaryOutcome.CANARY_POSTFLIGHT_READ_FAILED,
                dry_result=dry_result,
                worker_result=worker_result,
                worker_invocations=worker_invocations,
                after_graph=after_graph,
                deltas=deltas,
            )
        outcome = (
            PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_AFTER_COMMITTED_STAGE
            if cancelled_after
            else PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED
        )
        return self._result(
            request,
            outcome,
            dry_result,
            worker_result,
            worker_invocations,
            after_graph,
            deltas,
            "CANCELLED_AFTER_COMMITTED_STAGE" if cancelled_after else "NOT_CANCELLED",
        )

    @staticmethod
    def _validate_request(
        request: PaperControlledRuntimeSingleCycleCanaryRequest,
    ) -> PaperControlledRuntimeCanaryOutcome | None:
        cycle = request.cycle_request
        if (
            request.contract_version
            != PAPER_CONTROLLED_RUNTIME_CANARY_CONTRACT_VERSION
            or request.task_id != TASK_ID
            or request.task_id != request.target_identity.task_id
            or request.canary_run_id != request.target_identity.canary_run_id
            or request.correlation_id != cycle.correlation_id
            or request.expected_mutation_budget.stage is not request.expected_stage
            or request.symbol not in request.configuration.allowed_symbols
        ):
            return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
        if cycle.execution_mode is ExecutionMode.LIVE:
            return PaperControlledRuntimeCanaryOutcome.CANARY_LIVE_FORBIDDEN
        if cycle.execution_mode is not ExecutionMode.PAPER:
            return PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID
        if cycle.explicit_paper_authorization is not True:
            return PaperControlledRuntimeCanaryOutcome.CANARY_PAPER_AUTHORIZATION_MISSING
        if cycle.scope is not PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP:
            return PaperControlledRuntimeCanaryOutcome.CANARY_SCOPE_INVALID
        if cycle.max_stages != 1:
            return PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_LIMIT_INVALID
        return None

    @staticmethod
    def _validate_arming(
        request: PaperControlledRuntimeSingleCycleCanaryRequest,
    ) -> PaperControlledRuntimeCanaryOutcome | None:
        arming = request.arming
        if arming.expires_at <= request.evaluated_at:
            return PaperControlledRuntimeCanaryOutcome.CANARY_ARMING_EXPIRED
        if (
            arming.arming_contract_version
            != PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION
            or arming.task_id != request.task_id
            or arming.canary_run_id != request.canary_run_id
            or arming.configuration_id != request.configuration.configuration_id
            or arming.target_identity != request.target_identity
            or arming.expected_stage is not request.expected_stage
            or arming.expected_graph_fingerprint
            != request.expected_graph_fingerprint
            or arming.single_use is not True
            or arming.explicit_acknowledgement != CANARY_ACKNOWLEDGEMENT
        ):
            return PaperControlledRuntimeCanaryOutcome.CANARY_ARMING_INVALID
        return None

    @staticmethod
    def _dry_run_request(
        request: PaperControlledRuntimeSingleCycleCanaryRequest,
    ) -> PaperControlledRuntimeDryRunRequest:
        cycle = request.cycle_request
        ingestion_stage = (
            request.expected_stage
            is PaperControlledRuntimeCanaryStage.INGEST_COMMAND
        )
        entry_stage = (
            request.expected_stage
            is PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY
        )
        exit_stage = request.expected_stage in {
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER,
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER,
        }
        configuration = replace(
            request.configuration,
            runtime_action=PaperControlledRuntimeAction.DRY_RUN_PLAN,
            database_access_mode=PaperDatabaseAccessMode.ISOLATED_READ_ONLY,
        )
        return PaperControlledRuntimeDryRunRequest(
            request_id=f"{request.request_id}:dry-run",
            contract_version=PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION,
            configuration=configuration,
            symbol=request.symbol,
            cycle_id=cycle.cycle_id,
            correlation_id=request.correlation_id,
            command_id=cycle.command_id,
            created_at=request.evaluated_at,
            available_inputs=PaperControlledRuntimeAvailableInputSummary(
                approval_input_available=cycle.ingestion_request is not None,
                entry_input_available=cycle.entry_execution_request is not None,
                exit_window_available=cycle.exit_evaluation_request is not None,
                close_input_available=cycle.close_execution_request is not None,
            ),
            entry_order_id=None if ingestion_stage else cycle.entry_order_id,
            position_id=(
                None if ingestion_stage or entry_stage else cycle.position_id
            ),
            cursor_id=(
                cycle.cursor_id if exit_stage else None
            ),
            exit_decision_id=(
                cycle.exit_decision_id
                if request.expected_stage
                is PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE
                else None
            ),
            close_order_id=(
                cycle.close_order_id
                if request.expected_stage
                is PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE
                else None
            ),
        )

    @staticmethod
    def _exit_stage_outcome_matches(
        stage: PaperControlledRuntimeCanaryStage,
        worker_result: PaperLifecycleCycleResult,
    ) -> bool:
        child = worker_result.child_outcome_codes[0] if worker_result.child_outcome_codes else ""
        if stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER:
            return child == "NO_EXIT_TRIGGER_CURSOR_ADVANCED"
        if stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER:
            return child in {"EXIT_TRIGGERED_AND_CLOSE_ORDER_OPENED", "EXIT_PREPARED"}
        return True

    @staticmethod
    def _cancelled(
        request: PaperControlledRuntimeSingleCycleCanaryRequest,
    ) -> bool:
        authority = request.cancellation_authority
        return authority is not None and authority.is_cancelled() is True

    def _fault(self, point: PaperControlledRuntimeCanaryFaultPoint) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    def _failure(
        self,
        request: PaperControlledRuntimeSingleCycleCanaryRequest,
        outcome: PaperControlledRuntimeCanaryOutcome,
        *,
        dry_result: PaperControlledRuntimeDryRunResult | None = None,
        worker_result: PaperLifecycleCycleResult | None = None,
        worker_invocations: int = 0,
        after_graph: PaperLifecycleGraph | None = None,
        deltas: PaperControlledRuntimeCanaryRowCountDeltas | None = None,
        cancellation: str = "NOT_CANCELLED",
    ) -> PaperControlledRuntimeSingleCycleCanaryResult:
        return self._result(
            request,
            outcome,
            dry_result,
            worker_result,
            worker_invocations,
            after_graph,
            deltas or PaperControlledRuntimeCanaryRowCountDeltas(),
            cancellation,
        )

    @staticmethod
    def _result(
        request: PaperControlledRuntimeSingleCycleCanaryRequest,
        outcome: PaperControlledRuntimeCanaryOutcome,
        dry_result: PaperControlledRuntimeDryRunResult | None,
        worker_result: PaperLifecycleCycleResult | None,
        worker_invocations: int,
        after_graph: PaperLifecycleGraph | None,
        deltas: PaperControlledRuntimeCanaryRowCountDeltas,
        cancellation: str,
    ) -> PaperControlledRuntimeSingleCycleCanaryResult:
        child_outcome = (
            worker_result.child_outcome_codes[0]
            if worker_result and worker_result.child_outcome_codes
            else None
        )
        child_reason = (
            worker_result.child_reason_codes[0]
            if worker_result and worker_result.child_reason_codes
            else None
        )
        return PaperControlledRuntimeSingleCycleCanaryResult(
            request_id=request.request_id,
            canary_run_id=request.canary_run_id,
            outcome=outcome,
            reason_code=outcome.value[:MAX_SAFE_REASON_LENGTH],
            configuration_outcome=(
                "CONFIGURATION_VALID"
                if _canary_configuration_outcome(request.configuration) is None
                else "CONFIGURATION_INVALID"
            ),
            startup_gate_outcome=evaluate_controlled_runtime_startup_gate(
                request.configuration
            ).outcome.value,
            preflight_outcome=(
                "PREFLIGHT_PASSED"
                if worker_invocations
                else "PREFLIGHT_STOPPED"
            ),
            dry_run_outcome=(
                dry_result.dry_run_status.value
                if dry_result is not None
                else "NOT_RUN"
            ),
            initial_lifecycle_state=(
                dry_result.initial_lifecycle_state
                if dry_result is not None
                else None
            ),
            expected_stage=request.expected_stage,
            actual_attempted_stage=(
                request.expected_stage if worker_invocations else None
            ),
            worker_outcome=(
                worker_result.outcome.value if worker_result is not None else None
            ),
            child_outcome=child_outcome,
            child_reason=child_reason,
            postflight_lifecycle_state=(
                classify_paper_lifecycle_state(after_graph)
                if after_graph is not None
                else None
            ),
            mutation_budget_result=(
                "PASS"
                if worker_invocations
                and mutation_budget_matches(request.expected_mutation_budget, deltas)
                else "NOT_RUN"
                if not worker_invocations
                else "FAIL"
            ),
            row_count_deltas=deltas,
            entity_summary=_entity_summary(after_graph) if after_graph is not None else (),
            worker_invocations=worker_invocations,
            mutating_stage_invocations=(
                worker_result.stages_attempted if worker_result is not None else 0
            ),
            cancellation_outcome=cancellation,
            cleanup_outcome="CALLER_OWNED",
            correlation_id=request.correlation_id,
        )


def _bounded_json_file(path: str) -> dict[str, object] | None:
    candidate = Path(path)
    try:
        if candidate.stat().st_size > 64 * 1024:
            return None
        value = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def main(argv: list[str] | None = None) -> int:
    """Safe CLI acknowledgement surface; service wiring stays caller-owned."""

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--config")
    parser.add_argument("--request")
    parser.add_argument("--single-cycle-canary", action="store_true")
    args = parser.parse_args(argv)
    if (
        not args.single_cycle_canary
        or not args.config
        or not args.request
    ):
        print(
            json.dumps(
                {
                    "outcome": (
                        PaperControlledRuntimeCanaryOutcome
                        .CANARY_EXPLICIT_ACKNOWLEDGEMENT_MISSING.value
                    )
                },
                sort_keys=True,
            )
        )
        return 2
    configuration = _bounded_json_file(args.config)
    request = _bounded_json_file(args.request)
    if configuration is None or request is None:
        print(
            json.dumps(
                {
                    "outcome": (
                        PaperControlledRuntimeCanaryOutcome
                        .CANARY_CONFIGURATION_INVALID.value
                    )
                },
                sort_keys=True,
            )
        )
        return 2
    if (
        configuration.get("runtime_action")
        != PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY.value
        or configuration.get("target")
        != PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL.value
        or request.get("task_id") != TASK_ID
    ):
        print(
            json.dumps(
                {
                    "outcome": (
                        PaperControlledRuntimeCanaryOutcome
                        .CANARY_TARGET_FORBIDDEN.value
                    )
                },
                sort_keys=True,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "outcome": "CANARY_SERVICE_WIRING_REQUIRED",
                "target": PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL.value,
            },
            sort_keys=True,
        )
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "CANARY_ACKNOWLEDGEMENT",
    "EXPECTED_MIGRATION_HEAD",
    "PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION",
    "PAPER_CONTROLLED_RUNTIME_CANARY_CONTRACT_VERSION",
    "PAPER_CONTROLLED_RUNTIME_CANARY_TARGET_VERSION",
    "TASK_ID",
    "PaperControlledRuntimeCanaryArming",
    "PaperControlledRuntimeCanaryEntitySummary",
    "PaperControlledRuntimeCanaryFaultPoint",
    "PaperControlledRuntimeCanaryMutationBudget",
    "PaperControlledRuntimeCanaryOutcome",
    "PaperControlledRuntimeCanaryRowCountDeltas",
    "PaperControlledRuntimeCanaryStage",
    "PaperControlledRuntimeCanaryTargetIdentity",
    "PaperControlledRuntimeCanaryTargetValidation",
    "PaperControlledRuntimeSingleCycleCanaryRequest",
    "PaperControlledRuntimeSingleCycleCanaryResult",
    "PaperControlledRuntimeSingleCycleCanaryService",
    "SqlAlchemyPaperControlledRuntimeCanaryTargetValidator",
    "canary_ownership_marker",
    "main",
    "mutation_budget_matches",
    "paper_canary_graph_fingerprint",
    "valid_canary_target_identity",
)
