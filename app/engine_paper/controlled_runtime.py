"""Fail-closed configuration and read-only planning for the controlled PAPER worker.

This module deliberately has no executable runtime action.  It validates an
explicit, non-secret configuration and can inspect one bounded lifecycle graph
to describe what a separately authorized real cycle would attempt.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Final, Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.paper_models import PaperOrderRecord
from app.engine_paper.controlled_worker import (
    MAX_STAGES_PER_CYCLE,
    PaperLifecycleCycleScope,
    PaperLifecycleGraph,
    PaperLifecycleGraphLoadError,
    PaperLifecycleOrderNode,
    PaperLifecycleStage,
    PaperLifecycleState,
    classify_paper_lifecycle_state,
)
from app.engine_paper.repositories import MAX_GRAPH_ROWS, PaperCommandGraph, PaperRepositories
from app.engine_paper.repository_results import RepositoryOutcome
from app.engine_safety.paper_domain import ExecutionMode, require_identity, require_utc


PAPER_CONTROLLED_RUNTIME_CONFIGURATION_CONTRACT_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_CONFIGURATION_V1"
)
PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION: Final = (
    "PAPER_CONTROLLED_RUNTIME_DRY_RUN_V1"
)
MAX_CONFIGURATION_FILE_BYTES: Final = 64 * 1024
MAX_ALLOWED_SYMBOLS: Final = 32
MAX_BLOCKING_REASONS: Final = 16
MAX_MISSING_INPUTS: Final = 4
_SYMBOL_RE: Final = re.compile(r"[A-Z0-9]{2,32}\Z")
_SENSITIVE_FIELD_NAMES: Final = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "api_secret",
        "database_url",
        "database_uri",
        "authorization_header",
        "private_key",
    }
)


class PaperControlledRuntimeAction(StrEnum):
    VALIDATE_CONFIGURATION = "VALIDATE_CONFIGURATION"
    DRY_RUN_PLAN = "DRY_RUN_PLAN"
    SINGLE_CYCLE_CANARY = "SINGLE_CYCLE_CANARY"
    EXECUTE = "EXECUTE"
    START = "START"
    RUN_CONTINUOUS = "RUN_CONTINUOUS"
    DAEMON = "DAEMON"
    SCHEDULE = "SCHEDULE"
    LIVE = "LIVE"


class PaperControlledRuntimeTarget(StrEnum):
    ISOLATED_POSTGRESQL = "ISOLATED_POSTGRESQL"
    CONFIGURATION_ONLY = "CONFIGURATION_ONLY"
    PRODUCTION_READONLY_METADATA = "PRODUCTION_READONLY_METADATA"
    PRODUCTION_MUTATING = "PRODUCTION_MUTATING"


class PaperMarketDataInputMode(StrEnum):
    SUPPLIED_ONLY = "SUPPLIED_ONLY"


class PaperDatabaseAccessMode(StrEnum):
    NONE = "NONE"
    ISOLATED_READ_ONLY = "ISOLATED_READ_ONLY"
    ISOLATED_CANARY_READ_WRITE = "ISOLATED_CANARY_READ_WRITE"
    PRODUCTION_READONLY_METADATA = "PRODUCTION_READONLY_METADATA"


class PaperControlledRuntimeOutcome(StrEnum):
    CONFIGURATION_VALID = "CONFIGURATION_VALID"
    DRY_RUN_READY = "DRY_RUN_READY"
    DRY_RUN_NEXT_STAGE_READY = "DRY_RUN_NEXT_STAGE_READY"
    DRY_RUN_COMPLETE = "DRY_RUN_COMPLETE"
    DRY_RUN_BLOCKED_AWAITING_INPUT = "DRY_RUN_BLOCKED_AWAITING_INPUT"
    DRY_RUN_CONFIGURATION_ONLY = "DRY_RUN_CONFIGURATION_ONLY"
    RUNTIME_DISABLED = "RUNTIME_DISABLED"
    PAPER_AUTHORIZATION_MISSING = "PAPER_AUTHORIZATION_MISSING"
    MODE_OFF = "MODE_OFF"
    LIVE_FORBIDDEN = "LIVE_FORBIDDEN"
    UNSUPPORTED_RUNTIME_ACTION = "UNSUPPORTED_RUNTIME_ACTION"
    INVALID_TARGET = "INVALID_TARGET"
    INVALID_SCOPE = "INVALID_SCOPE"
    MAX_STAGES_EXCEEDED = "MAX_STAGES_EXCEEDED"
    SYMBOL_ALLOWLIST_EMPTY = "SYMBOL_ALLOWLIST_EMPTY"
    NETWORK_ACCESS_FORBIDDEN = "NETWORK_ACCESS_FORBIDDEN"
    POLLING_FORBIDDEN = "POLLING_FORBIDDEN"
    SCHEDULER_FORBIDDEN = "SCHEDULER_FORBIDDEN"
    DAEMON_FORBIDDEN = "DAEMON_FORBIDDEN"
    PRODUCTION_MUTATION_FORBIDDEN = "PRODUCTION_MUTATION_FORBIDDEN"
    RUNTIME_EXECUTION_NOT_IMPLEMENTED = "RUNTIME_EXECUTION_NOT_IMPLEMENTED"
    GRAPH_NOT_FOUND = "GRAPH_NOT_FOUND"
    SOURCE_GRAPH_INCONSISTENT = "SOURCE_GRAPH_INCONSISTENT"
    STALE_EXPECTED_VERSION = "STALE_EXPECTED_VERSION"
    SYMBOL_NOT_ALLOWED = "SYMBOL_NOT_ALLOWED"
    MISSING_APPROVAL_INPUT = "MISSING_APPROVAL_INPUT"
    MISSING_ENTRY_INPUT = "MISSING_ENTRY_INPUT"
    MISSING_EXIT_WINDOW = "MISSING_EXIT_WINDOW"
    MISSING_CLOSE_INPUT = "MISSING_CLOSE_INPUT"
    INVALID_DRY_RUN_REQUEST = "INVALID_DRY_RUN_REQUEST"
    READONLY_GRAPH_LOAD_FAILED = "READONLY_GRAPH_LOAD_FAILED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    UNKNOWN_CONFIGURATION_FIELD = "UNKNOWN_CONFIGURATION_FIELD"
    CONTRACT_VERSION_MISSING = "CONTRACT_VERSION_MISSING"
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    CONFIGURATION_TOO_LARGE = "CONFIGURATION_TOO_LARGE"
    CONFIGURATION_NOT_UTF8 = "CONFIGURATION_NOT_UTF8"
    DUPLICATE_CONFIGURATION_KEY = "DUPLICATE_CONFIGURATION_KEY"
    SENSITIVE_FIELD_FORBIDDEN = "SENSITIVE_FIELD_FORBIDDEN"
    CONFIGURATION_FILE_NOT_FOUND = "CONFIGURATION_FILE_NOT_FOUND"
    CONFIGURATION_FILE_READ_FAILED = "CONFIGURATION_FILE_READ_FAILED"
    CANCELLED = "CANCELLED"
    CANCELLED_AFTER_READ = "CANCELLED_AFTER_READ"


class PaperDryRunPlanReadiness(StrEnum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    CONDITIONAL = "CONDITIONAL"


class PaperGraphConsistencyStatus(StrEnum):
    NOT_ACCESSED = "NOT_ACCESSED"
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    NOT_FOUND = "NOT_FOUND"
    LOAD_FAILED = "LOAD_FAILED"


class PaperControlledRuntimeCancellationAuthority(Protocol):
    def is_cancelled(self) -> bool: ...


def _normalize_field_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _enum_or_original(enum_type: type[StrEnum], value: object) -> object:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(getattr(value, "value", value)).strip().upper())
    except (TypeError, ValueError):
        return value


def _normalize_symbols(values: object) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("allowed_symbols must be an array")
    if len(values) > MAX_ALLOWED_SYMBOLS:
        raise ValueError("allowed_symbols exceeds the hard bound")
    return tuple(str(value).strip().upper() for value in values)


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeConfiguration:
    contract_version: str = PAPER_CONTROLLED_RUNTIME_CONFIGURATION_CONTRACT_VERSION
    runtime_action: object = PaperControlledRuntimeAction.VALIDATE_CONFIGURATION
    target: object = PaperControlledRuntimeTarget.CONFIGURATION_ONLY
    execution_mode: object = ExecutionMode.OFF
    runtime_enabled: bool = False
    dry_run_enabled: bool = True
    explicit_paper_authorization: bool = False
    cycle_scope: object = PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
    max_stages_per_cycle: int = 1
    allowed_symbols: tuple[str, ...] = ()
    market_data_input_mode: object = PaperMarketDataInputMode.SUPPLIED_ONLY
    database_access_mode: object = PaperDatabaseAccessMode.NONE
    network_access_allowed: bool = False
    polling_allowed: bool = False
    scheduler_allowed: bool = False
    daemon_allowed: bool = False
    created_at: datetime | None = None
    configuration_id: str = "paper-controlled-runtime-default"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "runtime_action",
            _enum_or_original(PaperControlledRuntimeAction, self.runtime_action),
        )
        object.__setattr__(
            self, "target", _enum_or_original(PaperControlledRuntimeTarget, self.target)
        )
        object.__setattr__(
            self, "execution_mode", _enum_or_original(ExecutionMode, self.execution_mode)
        )
        object.__setattr__(
            self,
            "cycle_scope",
            _enum_or_original(PaperLifecycleCycleScope, self.cycle_scope),
        )
        object.__setattr__(
            self,
            "market_data_input_mode",
            _enum_or_original(PaperMarketDataInputMode, self.market_data_input_mode),
        )
        object.__setattr__(
            self,
            "database_access_mode",
            _enum_or_original(PaperDatabaseAccessMode, self.database_access_mode),
        )
        object.__setattr__(self, "allowed_symbols", _normalize_symbols(self.allowed_symbols))
        object.__setattr__(
            self, "configuration_id", require_identity(self.configuration_id, "configuration_id")
        )
        if self.created_at is not None:
            require_utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeConfigurationLoadResult:
    outcome: PaperControlledRuntimeOutcome
    configuration: PaperControlledRuntimeConfiguration | None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeStartupGateResult:
    outcome: PaperControlledRuntimeOutcome
    ready: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeAvailableInputSummary:
    approval_input_available: bool = False
    entry_input_available: bool = False
    exit_window_available: bool = False
    close_input_available: bool = False
    safety_exit_directive_available: bool = False

    def __post_init__(self) -> None:
        for item in fields(self):
            if not isinstance(getattr(self, item.name), bool):
                raise TypeError(f"{item.name} must be a boolean")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeDryRunRequest:
    request_id: str
    contract_version: str
    configuration: PaperControlledRuntimeConfiguration
    symbol: str
    cycle_id: str
    correlation_id: str
    command_id: str
    created_at: datetime
    available_inputs: PaperControlledRuntimeAvailableInputSummary
    entry_order_id: str | None = None
    position_id: str | None = None
    cursor_id: str | None = None
    exit_decision_id: str | None = None
    close_order_id: str | None = None
    expected_command_version: int | None = None
    expected_entry_order_version: int | None = None
    expected_position_version: int | None = None
    expected_cursor_version: int | None = None
    expected_close_order_version: int | None = None
    cancellation_authority: PaperControlledRuntimeCancellationAuthority | None = None

    def __post_init__(self) -> None:
        for name in ("request_id", "contract_version", "cycle_id", "correlation_id", "command_id"):
            object.__setattr__(self, name, require_identity(getattr(self, name), name))
        for name in (
            "entry_order_id",
            "position_id",
            "cursor_id",
            "exit_decision_id",
            "close_order_id",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_identity(value, name))
        normalized_symbol = str(self.symbol).strip().upper()
        object.__setattr__(self, "symbol", normalized_symbol)
        require_utc(self.created_at, "created_at")
        for name in (
            "expected_command_version",
            "expected_entry_order_version",
            "expected_position_version",
            "expected_cursor_version",
            "expected_close_order_version",
        ):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer")
        if not isinstance(self.available_inputs, PaperControlledRuntimeAvailableInputSummary):
            raise TypeError("available_inputs must be a typed immutable summary")


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeDryRunPlanItem:
    stage: PaperLifecycleStage
    readiness: PaperDryRunPlanReadiness
    required_input_kind: str | None
    input_available: bool
    child_service: str | None
    expected_persisted_preconditions: tuple[str, ...]
    expected_persisted_postconditions: tuple[str, ...]
    would_mutate_in_real_cycle: bool
    blocking_reason: str | None


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeReadOnlyProofSummary:
    fresh_session: bool
    exact_id_lookups: bool
    bounded_rows: bool
    database_read_only_transaction: bool
    write_locks: int
    business_mutations: int
    commits: int
    child_mutation_calls: int


@dataclass(frozen=True, slots=True)
class PaperControlledRuntimeDryRunResult:
    request_id: str
    configuration_id: str
    configuration_outcome: PaperControlledRuntimeOutcome
    startup_gate_outcome: PaperControlledRuntimeOutcome
    target: object
    execution_mode: object
    dry_run_status: PaperControlledRuntimeOutcome
    initial_lifecycle_state: PaperLifecycleState | None
    next_eligible_stage: PaperLifecycleStage | None
    stage_plan: tuple[PaperControlledRuntimeDryRunPlanItem, ...]
    missing_inputs: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    graph_consistency_status: PaperGraphConsistencyStatus
    read_only_proof: PaperControlledRuntimeReadOnlyProofSummary
    business_mutation_count: int
    commit_count: int
    child_mutation_call_count: int
    correlation_id: str


class _DuplicateKeyError(ValueError):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        normalized = str(key)
        if normalized in result:
            raise _DuplicateKeyError(normalized)
        result[normalized] = value
    return result


def _find_secret_field(value: object) -> str | None:
    stack = [value]
    compact_secrets = {item.replace("_", "") for item in _SENSITIVE_FIELD_NAMES}
    for _ in range(MAX_CONFIGURATION_FILE_BYTES):
        if not stack:
            return None
        current = stack.pop()
        if isinstance(current, Mapping):
            if len(current) > MAX_ALLOWED_SYMBOLS:
                return "configuration_structure_limit"
            for key, nested in current.items():
                normalized = _normalize_field_name(key)
                if (
                    normalized in _SENSITIVE_FIELD_NAMES
                    or normalized.replace("_", "") in compact_secrets
                ):
                    return normalized
                stack.append(nested)
        elif isinstance(current, list):
            if len(current) > MAX_ALLOWED_SYMBOLS:
                return "configuration_structure_limit"
            stack.extend(current)
    return "configuration_structure_limit"


class PaperControlledRuntimeConfigurationLoader:
    """Load only an explicit mapping or explicit bounded UTF-8 JSON file."""

    _field_names: Final = frozenset(
        item.name for item in fields(PaperControlledRuntimeConfiguration)
    )

    def load_mapping(
        self, source: Mapping[str, object]
    ) -> PaperControlledRuntimeConfigurationLoadResult:
        if not isinstance(source, Mapping):
            return self._failure(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
        secret_field = _find_secret_field(source)
        if secret_field is not None:
            if secret_field == "configuration_structure_limit":
                return self._failure(
                    PaperControlledRuntimeOutcome.INVALID_CONFIGURATION
                )
            return self._failure(
                PaperControlledRuntimeOutcome.SENSITIVE_FIELD_FORBIDDEN,
                f"FORBIDDEN_FIELD:{secret_field}",
            )
        unknown = sorted(set(source) - self._field_names)
        if unknown:
            return self._failure(
                PaperControlledRuntimeOutcome.UNKNOWN_CONFIGURATION_FIELD,
                *(f"UNKNOWN_FIELD:{name}" for name in unknown[:MAX_BLOCKING_REASONS]),
            )
        if "contract_version" not in source:
            return self._failure(PaperControlledRuntimeOutcome.CONTRACT_VERSION_MISSING)
        if source.get("contract_version") != PAPER_CONTROLLED_RUNTIME_CONFIGURATION_CONTRACT_VERSION:
            return self._failure(PaperControlledRuntimeOutcome.UNSUPPORTED_CONTRACT_VERSION)
        values = dict(source)
        created_at = values.get("created_at")
        if isinstance(created_at, str):
            try:
                values["created_at"] = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError:
                return self._failure(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
        try:
            configuration = PaperControlledRuntimeConfiguration(**values)
        except (TypeError, ValueError):
            return self._failure(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
        gate = evaluate_controlled_runtime_startup_gate(configuration)
        if gate.outcome not in {
            PaperControlledRuntimeOutcome.CONFIGURATION_VALID,
            PaperControlledRuntimeOutcome.DRY_RUN_READY,
        }:
            return PaperControlledRuntimeConfigurationLoadResult(
                gate.outcome, None, gate.reason_codes
            )
        return PaperControlledRuntimeConfigurationLoadResult(
            PaperControlledRuntimeOutcome.CONFIGURATION_VALID, configuration
        )

    def load_json_file(
        self, explicit_path: str | Path
    ) -> PaperControlledRuntimeConfigurationLoadResult:
        if not isinstance(explicit_path, (str, Path)) or not str(explicit_path).strip():
            return self._failure(PaperControlledRuntimeOutcome.CONFIGURATION_FILE_NOT_FOUND)
        path = Path(explicit_path)
        try:
            size = path.stat().st_size
        except (FileNotFoundError, OSError):
            return self._failure(PaperControlledRuntimeOutcome.CONFIGURATION_FILE_NOT_FOUND)
        if size > MAX_CONFIGURATION_FILE_BYTES:
            return self._failure(PaperControlledRuntimeOutcome.CONFIGURATION_TOO_LARGE)
        try:
            raw = path.read_bytes()
        except OSError:
            return self._failure(PaperControlledRuntimeOutcome.CONFIGURATION_FILE_READ_FAILED)
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return self._failure(PaperControlledRuntimeOutcome.CONFIGURATION_NOT_UTF8)
        try:
            parsed = json.loads(decoded, object_pairs_hook=_reject_duplicate_pairs)
        except _DuplicateKeyError:
            return self._failure(PaperControlledRuntimeOutcome.DUPLICATE_CONFIGURATION_KEY)
        except (json.JSONDecodeError, ValueError):
            return self._failure(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
        if not isinstance(parsed, Mapping):
            return self._failure(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
        return self.load_mapping(parsed)

    @staticmethod
    def _failure(
        outcome: PaperControlledRuntimeOutcome, *reason_codes: str
    ) -> PaperControlledRuntimeConfigurationLoadResult:
        return PaperControlledRuntimeConfigurationLoadResult(
            outcome, None, tuple(reason_codes)[:MAX_BLOCKING_REASONS]
        )


def _valid_symbol_allowlist(symbols: tuple[str, ...]) -> bool:
    return (
        len(symbols) <= MAX_ALLOWED_SYMBOLS
        and len(set(symbols)) == len(symbols)
        and all(_SYMBOL_RE.fullmatch(symbol) is not None and "*" not in symbol for symbol in symbols)
    )


def evaluate_controlled_runtime_startup_gate(
    configuration: PaperControlledRuntimeConfiguration,
) -> PaperControlledRuntimeStartupGateResult:
    """Pure deterministic startup/readiness policy with zero I/O."""

    if not isinstance(configuration, PaperControlledRuntimeConfiguration):
        return _gate(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
    if (
        configuration.contract_version
        != PAPER_CONTROLLED_RUNTIME_CONFIGURATION_CONTRACT_VERSION
    ):
        return _gate(PaperControlledRuntimeOutcome.UNSUPPORTED_CONTRACT_VERSION)
    action = configuration.runtime_action
    target = configuration.target
    mode = configuration.execution_mode
    if target is PaperControlledRuntimeTarget.PRODUCTION_MUTATING:
        return _gate(PaperControlledRuntimeOutcome.PRODUCTION_MUTATION_FORBIDDEN)
    if not isinstance(target, PaperControlledRuntimeTarget):
        return _gate(PaperControlledRuntimeOutcome.INVALID_TARGET)
    if action in {
        PaperControlledRuntimeAction.EXECUTE,
        PaperControlledRuntimeAction.START,
        PaperControlledRuntimeAction.RUN_CONTINUOUS,
        PaperControlledRuntimeAction.DAEMON,
        PaperControlledRuntimeAction.SCHEDULE,
        PaperControlledRuntimeAction.LIVE,
    }:
        return _gate(PaperControlledRuntimeOutcome.RUNTIME_EXECUTION_NOT_IMPLEMENTED)
    if not isinstance(action, PaperControlledRuntimeAction):
        return _gate(PaperControlledRuntimeOutcome.UNSUPPORTED_RUNTIME_ACTION)
    if mode is ExecutionMode.LIVE:
        return _gate(PaperControlledRuntimeOutcome.LIVE_FORBIDDEN)
    if not isinstance(mode, ExecutionMode):
        return _gate(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
    for field_name in (
        "runtime_enabled",
        "dry_run_enabled",
        "explicit_paper_authorization",
        "network_access_allowed",
        "polling_allowed",
        "scheduler_allowed",
        "daemon_allowed",
    ):
        if not isinstance(getattr(configuration, field_name), bool):
            return _gate(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
    if configuration.network_access_allowed:
        return _gate(PaperControlledRuntimeOutcome.NETWORK_ACCESS_FORBIDDEN)
    if configuration.polling_allowed:
        return _gate(PaperControlledRuntimeOutcome.POLLING_FORBIDDEN)
    if configuration.scheduler_allowed:
        return _gate(PaperControlledRuntimeOutcome.SCHEDULER_FORBIDDEN)
    if configuration.daemon_allowed:
        return _gate(PaperControlledRuntimeOutcome.DAEMON_FORBIDDEN)
    if configuration.market_data_input_mode is not PaperMarketDataInputMode.SUPPLIED_ONLY:
        return _gate(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
    if not isinstance(configuration.max_stages_per_cycle, int) or isinstance(
        configuration.max_stages_per_cycle, bool
    ):
        return _gate(PaperControlledRuntimeOutcome.INVALID_SCOPE)
    if not 1 <= configuration.max_stages_per_cycle <= MAX_STAGES_PER_CYCLE:
        return _gate(PaperControlledRuntimeOutcome.MAX_STAGES_EXCEEDED)
    if not isinstance(configuration.cycle_scope, PaperLifecycleCycleScope):
        return _gate(PaperControlledRuntimeOutcome.INVALID_SCOPE)
    if (
        configuration.cycle_scope
        is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
        and configuration.max_stages_per_cycle != 1
    ):
        return _gate(PaperControlledRuntimeOutcome.INVALID_SCOPE)
    if not _valid_symbol_allowlist(configuration.allowed_symbols):
        return _gate(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)
    if mode is ExecutionMode.OFF and configuration.runtime_enabled:
        return _gate(PaperControlledRuntimeOutcome.RUNTIME_DISABLED)
    if mode is ExecutionMode.PAPER:
        if not configuration.dry_run_enabled:
            return _gate(PaperControlledRuntimeOutcome.RUNTIME_DISABLED)
        if not configuration.explicit_paper_authorization:
            return _gate(PaperControlledRuntimeOutcome.PAPER_AUTHORIZATION_MISSING)
        if action not in {
            PaperControlledRuntimeAction.DRY_RUN_PLAN,
            PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY,
        }:
            return _gate(PaperControlledRuntimeOutcome.UNSUPPORTED_RUNTIME_ACTION)
    if action is PaperControlledRuntimeAction.VALIDATE_CONFIGURATION:
        return _gate(PaperControlledRuntimeOutcome.CONFIGURATION_VALID, ready=True)
    if mode is ExecutionMode.OFF:
        return _gate(PaperControlledRuntimeOutcome.MODE_OFF)
    if mode is ExecutionMode.PAPER:
        if not configuration.runtime_enabled:
            return _gate(PaperControlledRuntimeOutcome.RUNTIME_DISABLED)
        if not configuration.allowed_symbols:
            return _gate(PaperControlledRuntimeOutcome.SYMBOL_ALLOWLIST_EMPTY)
        if target is PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL:
            expected_access = (
                PaperDatabaseAccessMode.ISOLATED_CANARY_READ_WRITE
                if action is PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY
                else PaperDatabaseAccessMode.ISOLATED_READ_ONLY
            )
            if configuration.database_access_mode is not expected_access:
                return _gate(PaperControlledRuntimeOutcome.INVALID_TARGET)
            return _gate(PaperControlledRuntimeOutcome.DRY_RUN_READY, ready=True)
        if target in {
            PaperControlledRuntimeTarget.CONFIGURATION_ONLY,
            PaperControlledRuntimeTarget.PRODUCTION_READONLY_METADATA,
        }:
            if configuration.database_access_mode not in {
                PaperDatabaseAccessMode.NONE,
                PaperDatabaseAccessMode.PRODUCTION_READONLY_METADATA,
            }:
                return _gate(PaperControlledRuntimeOutcome.INVALID_TARGET)
            return _gate(PaperControlledRuntimeOutcome.CONFIGURATION_VALID, ready=True)
    return _gate(PaperControlledRuntimeOutcome.INVALID_CONFIGURATION)


def _gate(
    outcome: PaperControlledRuntimeOutcome, *, ready: bool = False
) -> PaperControlledRuntimeStartupGateResult:
    reasons = () if ready else (outcome.value,)
    return PaperControlledRuntimeStartupGateResult(outcome, ready, reasons)


class SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader:
    """Fresh-session exact-ID loader with a rollback-only transaction."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self.last_database_read_only_transaction = False

    def load(self, command_id: str) -> PaperLifecycleGraph:
        exact_command_id = require_identity(command_id, "command_id")
        session = self._session_factory()
        transaction = session.begin()
        read_only = False
        try:
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                session.execute(text("SET TRANSACTION READ ONLY"))
                read_only = True
            repositories = PaperRepositories(session)
            result = repositories.commands.get_command_graph(
                exact_command_id, limit=MAX_GRAPH_ROWS
            )
            if result.outcome is RepositoryOutcome.NOT_FOUND:
                return PaperLifecycleGraph(command_id=exact_command_id)
            if (
                result.outcome is not RepositoryOutcome.EXISTING_IDEMPOTENT
                or not isinstance(result.value, PaperCommandGraph)
            ):
                raise PaperLifecycleGraphLoadError(result.outcome, result.reason_code)
            graph = result.value
            role_rows = tuple(
                session.execute(
                    select(PaperOrderRecord.order_id, PaperOrderRecord.order_role)
                    .where(PaperOrderRecord.command_id == exact_command_id)
                    .order_by(PaperOrderRecord.order_role, PaperOrderRecord.order_id)
                    .limit(3)
                )
            )
            role_by_id = {str(row.order_id): str(row.order_role) for row in role_rows}
            bounded_limit_reached = any(
                len(values) >= MAX_GRAPH_ROWS
                for values in (
                    graph.orders,
                    graph.fills,
                    graph.positions,
                    graph.exit_decisions,
                    graph.cursors,
                    graph.order_events,
                    graph.journal,
                )
            ) or len(role_rows) != len(graph.orders)
            return PaperLifecycleGraph(
                command_id=exact_command_id,
                command=graph.command,
                orders=tuple(
                    PaperLifecycleOrderNode(role_by_id.get(order.order_id, ""), order)
                    for order in graph.orders
                ),
                fills=graph.fills,
                positions=graph.positions,
                exit_decisions=graph.exit_decisions,
                cursors=graph.cursors,
                order_events=graph.order_events,
                journal=graph.journal,
                bounded_limit_reached=bounded_limit_reached,
            )
        finally:
            self.last_database_read_only_transaction = read_only
            if transaction.is_active:
                transaction.rollback()
            session.close()


_STAGE_SPEC: Final = MappingProxyType({
    PaperLifecycleStage.INGEST_COMMAND: (
        "APPROVAL_INPUT",
        "PaperCommandIngestionService",
        ("approvals-only authority; command absent",),
        ("command and OPEN ENTRY order durably exist",),
        PaperControlledRuntimeOutcome.MISSING_APPROVAL_INPUT,
    ),
    PaperLifecycleStage.EXECUTE_ENTRY: (
        "ENTRY_INPUT",
        "PaperOrderExecutionService.execute_entry",
        ("ENTRY order is OPEN at expected version",),
        ("ENTRY fill, OPEN position, and exit cursor durably exist",),
        PaperControlledRuntimeOutcome.MISSING_ENTRY_INPUT,
    ),
    PaperLifecycleStage.EVALUATE_EXIT: (
        "EXIT_WINDOW",
        "PaperExitEvaluationService",
        ("position OPEN and cursor at expected version",),
        ("cursor advances or exit decision, CLOSING position, CLOSE order exist",),
        PaperControlledRuntimeOutcome.MISSING_EXIT_WINDOW,
    ),
    PaperLifecycleStage.EXECUTE_CLOSE: (
        "CLOSE_INPUT",
        "PaperOrderExecutionService.execute_close",
        ("position CLOSING and CLOSE order OPEN at expected versions",),
        ("CLOSE fill and CLOSED position durably exist",),
        PaperControlledRuntimeOutcome.MISSING_CLOSE_INPUT,
    ),
})
_STAGE_SEQUENCE: Final = (
    PaperLifecycleStage.INGEST_COMMAND,
    PaperLifecycleStage.EXECUTE_ENTRY,
    PaperLifecycleStage.EVALUATE_EXIT,
    PaperLifecycleStage.EXECUTE_CLOSE,
)
_NEXT_STAGE: Final = MappingProxyType({
    PaperLifecycleState.APPROVALS_ONLY: PaperLifecycleStage.INGEST_COMMAND,
    PaperLifecycleState.ENTRY_ORDER_OPEN: PaperLifecycleStage.EXECUTE_ENTRY,
    PaperLifecycleState.POSITION_OPEN_CURSOR_READY: PaperLifecycleStage.EVALUATE_EXIT,
    PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN: PaperLifecycleStage.EXECUTE_CLOSE,
})


class PaperControlledRuntimeDryRunService:
    """Build a bounded plan; never receives or invokes a mutating child service."""

    def __init__(
        self,
        graph_loader: SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader | None = None,
    ) -> None:
        self._graph_loader = graph_loader

    def plan(
        self, request: PaperControlledRuntimeDryRunRequest
    ) -> PaperControlledRuntimeDryRunResult:
        proof = self._proof(False)
        if not isinstance(request, PaperControlledRuntimeDryRunRequest):
            raise TypeError("request must be PaperControlledRuntimeDryRunRequest")
        gate = evaluate_controlled_runtime_startup_gate(request.configuration)
        if request.contract_version != PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.INVALID_DRY_RUN_REQUEST,
                proof=proof,
                blockers=(PaperControlledRuntimeOutcome.INVALID_DRY_RUN_REQUEST.value,),
            )
        if gate.outcome not in {
            PaperControlledRuntimeOutcome.CONFIGURATION_VALID,
            PaperControlledRuntimeOutcome.DRY_RUN_READY,
        }:
            return self._result(
                request, gate.outcome, gate.outcome, proof=proof, blockers=gate.reason_codes
            )
        if request.cancellation_authority is not None and request.cancellation_authority.is_cancelled():
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.CANCELLED,
                proof=proof,
                blockers=(PaperControlledRuntimeOutcome.CANCELLED.value,),
            )
        configuration = request.configuration
        if configuration.target in {
            PaperControlledRuntimeTarget.CONFIGURATION_ONLY,
            PaperControlledRuntimeTarget.PRODUCTION_READONLY_METADATA,
        }:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.DRY_RUN_CONFIGURATION_ONLY,
                proof=proof,
            )
        if configuration.runtime_action is not PaperControlledRuntimeAction.DRY_RUN_PLAN:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.DRY_RUN_CONFIGURATION_ONLY,
                proof=proof,
            )
        if _SYMBOL_RE.fullmatch(request.symbol) is None:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.INVALID_DRY_RUN_REQUEST,
                proof=proof,
                blockers=(PaperControlledRuntimeOutcome.INVALID_DRY_RUN_REQUEST.value,),
            )
        if request.symbol not in configuration.allowed_symbols:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.SYMBOL_NOT_ALLOWED,
                proof=proof,
                blockers=(PaperControlledRuntimeOutcome.SYMBOL_NOT_ALLOWED.value,),
            )
        if self._graph_loader is None:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.READONLY_GRAPH_LOAD_FAILED,
                proof=proof,
                graph_status=PaperGraphConsistencyStatus.LOAD_FAILED,
                blockers=(PaperControlledRuntimeOutcome.READONLY_GRAPH_LOAD_FAILED.value,),
            )
        try:
            graph = self._graph_loader.load(request.command_id)
        except Exception:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.READONLY_GRAPH_LOAD_FAILED,
                proof=proof,
                graph_status=PaperGraphConsistencyStatus.LOAD_FAILED,
                blockers=(PaperControlledRuntimeOutcome.READONLY_GRAPH_LOAD_FAILED.value,),
            )
        proof = self._proof(self._graph_loader.last_database_read_only_transaction)
        if request.cancellation_authority is not None and request.cancellation_authority.is_cancelled():
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.CANCELLED_AFTER_READ,
                proof=proof,
                blockers=(PaperControlledRuntimeOutcome.CANCELLED_AFTER_READ.value,),
            )
        if graph.command is None and self._requires_existing_graph(request):
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.GRAPH_NOT_FOUND,
                proof=proof,
                graph_status=PaperGraphConsistencyStatus.NOT_FOUND,
                blockers=(PaperControlledRuntimeOutcome.GRAPH_NOT_FOUND.value,),
            )
        if graph.command is not None and graph.command.symbol != request.symbol:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.SYMBOL_NOT_ALLOWED,
                proof=proof,
                graph_status=PaperGraphConsistencyStatus.NOT_FOUND,
                blockers=(PaperControlledRuntimeOutcome.SYMBOL_NOT_ALLOWED.value,),
            )
        if self._identity_selector_missing(request, graph):
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.GRAPH_NOT_FOUND,
                proof=proof,
                graph_status=PaperGraphConsistencyStatus.NOT_FOUND,
                blockers=(PaperControlledRuntimeOutcome.GRAPH_NOT_FOUND.value,),
            )
        state = classify_paper_lifecycle_state(graph)
        if state is PaperLifecycleState.INCONSISTENT:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.SOURCE_GRAPH_INCONSISTENT,
                state=state,
                proof=proof,
                graph_status=PaperGraphConsistencyStatus.INCONSISTENT,
                blockers=(PaperControlledRuntimeOutcome.SOURCE_GRAPH_INCONSISTENT.value,),
            )
        stale = self._stale_expected_version(request, graph)
        if stale:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.STALE_EXPECTED_VERSION,
                state=state,
                proof=proof,
                blockers=(PaperControlledRuntimeOutcome.STALE_EXPECTED_VERSION.value,),
            )
        if state is PaperLifecycleState.POSITION_CLOSED:
            return self._result(
                request,
                gate.outcome,
                PaperControlledRuntimeOutcome.DRY_RUN_COMPLETE,
                state=state,
                proof=proof,
            )
        stage = _NEXT_STAGE[state]
        plan, missing = self._build_plan(request, stage)
        status = (
            PaperControlledRuntimeOutcome.DRY_RUN_BLOCKED_AWAITING_INPUT
            if missing
            else PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY
        )
        blockers = tuple(missing)
        return self._result(
            request,
            gate.outcome,
            status,
            state=state,
            next_stage=stage,
            plan=plan,
            missing=tuple(missing),
            blockers=blockers,
            proof=proof,
        )

    @staticmethod
    def _requires_existing_graph(request: PaperControlledRuntimeDryRunRequest) -> bool:
        return any(
            value is not None
            for value in (
                request.entry_order_id,
                request.position_id,
                request.cursor_id,
                request.exit_decision_id,
                request.close_order_id,
                request.expected_command_version,
                request.expected_entry_order_version,
                request.expected_position_version,
                request.expected_cursor_version,
                request.expected_close_order_version,
            )
        )

    @staticmethod
    def _identity_selector_missing(
        request: PaperControlledRuntimeDryRunRequest, graph: PaperLifecycleGraph
    ) -> bool:
        graph_ids = {
            "entry_order_id": {
                item.order.order_id for item in graph.orders if item.role == "ENTRY"
            },
            "position_id": {item.position_id for item in graph.positions},
            "cursor_id": {item.cursor_id for item in graph.cursors},
            "exit_decision_id": {
                item.exit_decision_id for item in graph.exit_decisions
            },
            "close_order_id": {
                item.order.order_id for item in graph.orders if item.role == "EXIT"
            },
        }
        return any(
            getattr(request, field_name) is not None
            and getattr(request, field_name) not in identities
            for field_name, identities in graph_ids.items()
        )

    @staticmethod
    def _stale_expected_version(
        request: PaperControlledRuntimeDryRunRequest, graph: PaperLifecycleGraph
    ) -> bool:
        entry = next((item.order for item in graph.orders if item.role == "ENTRY"), None)
        close = next((item.order for item in graph.orders if item.role == "EXIT"), None)
        position = graph.positions[0] if len(graph.positions) == 1 else None
        cursor = graph.cursors[0] if len(graph.cursors) == 1 else None
        checks = (
            (request.expected_command_version, graph.command),
            (request.expected_entry_order_version, entry),
            (request.expected_position_version, position),
            (request.expected_cursor_version, cursor),
            (request.expected_close_order_version, close),
        )
        return any(
            expected is not None
            and (value is None or getattr(value, "version", None) != expected)
            for expected, value in checks
        )

    @staticmethod
    def _input_available(
        summary: PaperControlledRuntimeAvailableInputSummary,
        stage: PaperLifecycleStage,
    ) -> bool:
        return {
            PaperLifecycleStage.INGEST_COMMAND: summary.approval_input_available,
            PaperLifecycleStage.EXECUTE_ENTRY: summary.entry_input_available,
            PaperLifecycleStage.EVALUATE_EXIT: (
                summary.exit_window_available or summary.safety_exit_directive_available
            ),
            PaperLifecycleStage.EXECUTE_CLOSE: summary.close_input_available,
        }[stage]

    def _build_plan(
        self, request: PaperControlledRuntimeDryRunRequest, next_stage: PaperLifecycleStage
    ) -> tuple[tuple[PaperControlledRuntimeDryRunPlanItem, ...], list[str]]:
        start = _STAGE_SEQUENCE.index(next_stage)
        count = request.configuration.max_stages_per_cycle
        if (
            request.configuration.cycle_scope
            is PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP
        ):
            count = 1
        stages = _STAGE_SEQUENCE[start : start + count]
        items: list[PaperControlledRuntimeDryRunPlanItem] = []
        missing: list[str] = []
        for index, stage in enumerate(stages):
            input_kind, service, preconditions, postconditions, missing_outcome = _STAGE_SPEC[stage]
            available = self._input_available(request.available_inputs, stage)
            if index == 0:
                readiness = (
                    PaperDryRunPlanReadiness.READY
                    if available
                    else PaperDryRunPlanReadiness.BLOCKED
                )
                blocking = None if available else missing_outcome.value
                if blocking is not None:
                    missing.append(blocking)
            else:
                readiness = PaperDryRunPlanReadiness.CONDITIONAL
                blocking = "FOLLOWING_STAGE_REQUIRES_FUTURE_PERSISTED_PRECONDITION"
            items.append(
                PaperControlledRuntimeDryRunPlanItem(
                    stage,
                    readiness,
                    input_kind,
                    available,
                    service,
                    preconditions,
                    postconditions,
                    True,
                    blocking,
                )
            )
        return tuple(items), missing[:MAX_MISSING_INPUTS]

    @staticmethod
    def _proof(database_read_only_transaction: bool) -> PaperControlledRuntimeReadOnlyProofSummary:
        return PaperControlledRuntimeReadOnlyProofSummary(
            fresh_session=True,
            exact_id_lookups=True,
            bounded_rows=True,
            database_read_only_transaction=database_read_only_transaction,
            write_locks=0,
            business_mutations=0,
            commits=0,
            child_mutation_calls=0,
        )

    @staticmethod
    def _result(
        request: PaperControlledRuntimeDryRunRequest,
        configuration_outcome: PaperControlledRuntimeOutcome,
        status: PaperControlledRuntimeOutcome,
        *,
        state: PaperLifecycleState | None = None,
        next_stage: PaperLifecycleStage | None = None,
        plan: tuple[PaperControlledRuntimeDryRunPlanItem, ...] = (),
        missing: tuple[str, ...] = (),
        blockers: tuple[str, ...] = (),
        graph_status: PaperGraphConsistencyStatus = PaperGraphConsistencyStatus.CONSISTENT,
        proof: PaperControlledRuntimeReadOnlyProofSummary,
    ) -> PaperControlledRuntimeDryRunResult:
        if state is None and graph_status is PaperGraphConsistencyStatus.CONSISTENT:
            graph_status = PaperGraphConsistencyStatus.NOT_ACCESSED
        startup_gate_outcome = configuration_outcome
        configuration_outcome = (
            PaperControlledRuntimeOutcome.CONFIGURATION_VALID
            if configuration_outcome
            in {
                PaperControlledRuntimeOutcome.CONFIGURATION_VALID,
                PaperControlledRuntimeOutcome.DRY_RUN_READY,
            }
            else configuration_outcome
        )
        return PaperControlledRuntimeDryRunResult(
            request.request_id,
            request.configuration.configuration_id,
            configuration_outcome,
            startup_gate_outcome,
            request.configuration.target,
            request.configuration.execution_mode,
            status,
            state,
            next_stage,
            plan[:MAX_STAGES_PER_CYCLE],
            missing[:MAX_MISSING_INPUTS],
            blockers[:MAX_BLOCKING_REASONS],
            graph_status,
            proof,
            0,
            0,
            0,
            request.correlation_id,
        )
