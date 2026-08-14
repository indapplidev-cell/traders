"""Secret-free contracts for bounded production PAPER preparation.

The executor never resolves a database URL, opens a protected binding, or
handles credential material.  Those responsibilities live behind the concrete
backend. Planning reads only sanitized postconditions through the trusted
backend and therefore consumes no caller-provided secret.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Mapping, Protocol

from app.engine_paper.accounting import PaperAccountIdentity


PRODUCTION_PAPER_RUNTIME_ROLE: Final = "traders_paper_runtime"
PRODUCTION_READONLY_ROLE: Final = "traders_readonly_api"
EXPECTED_START_ALEMBIC: Final = "0008_engine_orchestrator_freshness_retry"
EXPECTED_PREVIOUS_ALEMBIC: Final = "0014_paper_canary_selection_policy"
EXPECTED_FINAL_ALEMBIC: Final = "0015_trading_universe_activation"
SUPPORTED_PREPARATION_REVISIONS: Final = frozenset({
    EXPECTED_START_ALEMBIC, EXPECTED_PREVIOUS_ALEMBIC, EXPECTED_FINAL_ALEMBIC,
})
IDENTITY_KEYS: Final = (
    "PAPER_PRODUCTION_ACCOUNT_ID",
    "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID",
    "PAPER_PRODUCTION_CURRENCY",
)
_IDENTIFIER = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,127}$")
_TARGET_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}$")
_FIXTURE_MARKERS = ("TEST", "FIXTURE", "EXAMPLE", "DEMO", "PYTEST")


class PaperProductionIdentityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PaperProductionAccountIdentityBinding:
    """Stable non-secret deployment identity; rotation is an operator change."""

    paper_account_id: str
    accounting_session_id: str
    currency: str = "USDT"
    source: str = "OPERATOR_NON_SECRET_PRODUCTION_CONFIGURATION"

    def __post_init__(self) -> None:
        normalized: list[str] = []
        for field, value in (("paper_account_id", self.paper_account_id),
                             ("accounting_session_id", self.accounting_session_id)):
            if not isinstance(value, str) or value != value.strip() or not _IDENTIFIER.fullmatch(value):
                raise PaperProductionIdentityError(f"INVALID_PRODUCTION_{field.upper()}")
            canonical = value.upper()
            if any(marker in canonical for marker in _FIXTURE_MARKERS):
                raise PaperProductionIdentityError("TEST_FIXTURE_IDENTITY_DENIED")
            normalized.append(canonical)
        if self.currency != "USDT" or self.source != "OPERATOR_NON_SECRET_PRODUCTION_CONFIGURATION":
            raise PaperProductionIdentityError("INVALID_PRODUCTION_IDENTITY_BINDING")
        object.__setattr__(self, "paper_account_id", normalized[0])
        object.__setattr__(self, "accounting_session_id", normalized[1])

    @classmethod
    def from_configuration(cls, values: Mapping[str, str]) -> "PaperProductionAccountIdentityBinding":
        if set(values) != set(IDENTITY_KEYS):
            raise PaperProductionIdentityError("PRODUCTION_IDENTITY_BINDING_MISSING_OR_CONFLICTING")
        return cls(values[IDENTITY_KEYS[0]], values[IDENTITY_KEYS[1]], values[IDENTITY_KEYS[2]])

    def account_identity(self) -> PaperAccountIdentity:
        return PaperAccountIdentity(self.paper_account_id, self.accounting_session_id, self.currency)


class PaperPreparationAction(StrEnum):
    ENSURE_RUNTIME_ROLE = "ENSURE_RUNTIME_ROLE"
    APPLY_RUNTIME_GRANTS = "APPLY_RUNTIME_GRANTS"
    APPLY_READONLY_REPORTING_GRANTS = "APPLY_READONLY_REPORTING_GRANTS"
    BIND_RUNTIME_CREDENTIAL = "BIND_RUNTIME_CREDENTIAL"
    VALIDATE_RUNTIME_BINDING = "VALIDATE_RUNTIME_BINDING"
    DEPLOY_DISABLED_RUNTIME_CONFIGURATION = "DEPLOY_DISABLED_RUNTIME_CONFIGURATION"
    DEPLOY_READONLY_API_NARROW = "DEPLOY_READONLY_API_NARROW"


ALL_PREPARATION_ACTIONS: Final = tuple(PaperPreparationAction)


class PaperPreparationPhase(StrEnum):
    PRE_MIGRATION_READY = "PRE_MIGRATION_READY"
    PARTIAL_RESUMABLE = "PARTIAL_RESUMABLE"
    COMPLETED = "COMPLETED"
    INCOMPATIBLE = "INCOMPATIBLE"


def classify_preparation_phase(
    alembic_revision: str, *, preparation_complete: bool, privilege_drift: bool = False,
    incompatible_postcondition: bool = False,
) -> PaperPreparationPhase:
    if (privilege_drift or incompatible_postcondition
            or alembic_revision not in SUPPORTED_PREPARATION_REVISIONS):
        return PaperPreparationPhase.INCOMPATIBLE
    if alembic_revision == EXPECTED_START_ALEMBIC:
        return PaperPreparationPhase.PRE_MIGRATION_READY
    return (PaperPreparationPhase.COMPLETED if preparation_complete
            else PaperPreparationPhase.PARTIAL_RESUMABLE)


class PaperPreparationConsumerHealth(StrEnum):
    NOT_CHECKED = "NOT_CHECKED"
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"


class PaperPreparationFinding(StrEnum):
    READY = "READY"
    IDENTITY_BINDING_MISSING = "IDENTITY_BINDING_MISSING"
    PROTECTED_BACKEND_MISSING = "PROTECTED_BACKEND_MISSING"
    RUNTIME_CREDENTIAL_BINDING_MISSING = "RUNTIME_CREDENTIAL_BINDING_MISSING"
    RUNTIME_GRANTS_NOT_READY = "RUNTIME_GRANTS_NOT_READY"
    READONLY_GRANTS_NOT_READY = "READONLY_GRANTS_NOT_READY"
    SCHEMA_NOT_READY = "SCHEMA_NOT_READY"
    BASELINE_MISSING = "BASELINE_MISSING"
    READONLY_REPORTING_NOT_DEPLOYED = "READONLY_REPORTING_NOT_DEPLOYED"
    EXISTING_ROLE_PRIVILEGE_DRIFT = "EXISTING_ROLE_PRIVILEGE_DRIFT"
    TARGET_ENVIRONMENT_MISMATCH = "TARGET_ENVIRONMENT_MISMATCH"
    MUTATION_BUDGET_EXCEEDED = "MUTATION_BUDGET_EXCEEDED"
    EXECUTION_NOT_AUTHORIZED = "EXECUTION_NOT_AUTHORIZED"
    SAFE_FAILURE = "SAFE_FAILURE"


@dataclass(frozen=True, slots=True)
class PaperProductionTargetGuard:
    database_target_id: str
    environment: str = "PRODUCTION"
    postgresql_major: int = 16
    expected_start_alembic: str = EXPECTED_START_ALEMBIC
    control_state: str = "DISABLED"
    live_enabled: bool = False

    def __post_init__(self) -> None:
        if (not _TARGET_IDENTIFIER.fullmatch(self.database_target_id)
                or self.environment != "PRODUCTION" or self.postgresql_major != 16
                or self.expected_start_alembic not in SUPPORTED_PREPARATION_REVISIONS
                or self.control_state != "DISABLED" or self.live_enabled):
            raise ValueError("PRODUCTION_TARGET_GUARD_MISMATCH")


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationMutationBudget:
    max_runtime_role_create: int = 1
    max_runtime_grant_reconciliation: int = 1
    max_readonly_grant_reconciliation: int = 1
    max_runtime_binding_write: int = 1
    max_disabled_runtime_deployment: int = 1
    max_readonly_api_deployment: int = 1

    def __post_init__(self) -> None:
        if tuple(getattr(self, name) for name in self.__dataclass_fields__) != (1, 1, 1, 1, 1, 1):
            raise ValueError("UNBOUNDED_PRODUCTION_PREPARATION_BUDGET")


@dataclass(frozen=True, slots=True)
class PaperProductionExecutionAuthorization:
    production_acknowledgement: str
    allowed_actions: tuple[PaperPreparationAction, ...]

    def __post_init__(self) -> None:
        if self.production_acknowledgement != "I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS":
            raise ValueError("PRODUCTION_EXECUTION_ACKNOWLEDGEMENT_REQUIRED")
        if not self.allowed_actions or len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ValueError("EXPLICIT_UNIQUE_ACTION_SET_REQUIRED")
        if any(action not in ALL_PREPARATION_ACTIONS for action in self.allowed_actions):
            raise ValueError("FORBIDDEN_PREPARATION_ACTION")
        ordered = tuple(action for action in ALL_PREPARATION_ACTIONS if action in self.allowed_actions)
        if self.allowed_actions != ordered:
            raise ValueError("PREPARATION_ACTION_ORDER_INVALID")


@dataclass(frozen=True, slots=True)
class DatabaseGrant:
    table: str
    operations: tuple[str, ...]


def normalize_database_grants(
    rows: tuple[tuple[str, str, str], ...],
) -> frozenset[tuple[str, str, bool]]:
    """Normalize PostgreSQL grant metadata as an order-independent semantic set."""
    return frozenset(
        (table.strip().lower(), privilege.strip().upper(), grantable.strip().upper() == "YES")
        for table, privilege, grantable in rows
    )


def classify_database_privilege_drift(
    rows: tuple[tuple[str, str, str], ...],
    accepted: tuple[DatabaseGrant, ...],
    *,
    memberships: int = 0,
    ownership: int = 0,
    non_table_acl: int = 0,
) -> bool:
    expected = frozenset(
        (item.table.strip().lower(), operation.strip().upper())
        for item in accepted for operation in item.operations
    )
    normalized = normalize_database_grants(rows)
    return bool(
        memberships or ownership or non_table_acl
        or any(grantable or (table, privilege) not in expected
               for table, privilege, grantable in normalized)
    )


def required_database_privileges_present(
    rows: tuple[tuple[str, str, str], ...], required: tuple[DatabaseGrant, ...],
) -> bool:
    normalized = normalize_database_grants(rows)
    present = frozenset((table, privilege) for table, privilege, _ in normalized)
    expected = frozenset(
        (item.table.strip().lower(), operation.strip().upper())
        for item in required for operation in item.operations
    )
    return expected <= present


@dataclass(frozen=True, slots=True)
class PaperRuntimeRolePolicy:
    login: bool = True
    superuser: bool = False
    createdb: bool = False
    createrole: bool = False
    replication: bool = False
    bypassrls: bool = False
    grant_option: bool = False
    ownership: bool = False
    memberships: tuple[str, ...] = ()


RUNTIME_ROLE_POLICY: Final = PaperRuntimeRolePolicy()
RUNTIME_READ_TABLES: Final = (
    "alembic_version", "candles_1m", "candles_5m", "candles_15m", "candles_1h",
    "candles_4h", "candles_1d", "market_data_sync_state", "online_pipeline_runs",
    "online_pipeline_results", "paper_account_baselines",
)
RUNTIME_WRITE_TABLES: Final = (
    "paper_simulation_policies", "paper_execution_commands", "paper_orders",
    "paper_order_events", "paper_fills", "paper_positions",
    "paper_exit_evaluation_cursors", "paper_exit_decisions", "paper_journal_entries",
    "paper_first_canary_sessions",
)
RUNTIME_UPDATE_TABLES: Final = (
    "paper_execution_commands", "paper_orders", "paper_positions",
    "paper_exit_evaluation_cursors", "paper_first_canary_sessions",
)
READONLY_PAPER_TABLES: Final = (
    "alembic_version", "paper_account_baselines",
) + RUNTIME_WRITE_TABLES
# Authoritative pre-PAPER Readonly API relation contract. These are the only
# relations used by the original nine-route production API and remain valid
# when the separately authorized PAPER reporting SELECT grants are added.
READONLY_BASELINE_TABLES: Final = (
    "candles_15m", "online_pipeline_results", "online_pipeline_runs",
)
RUNTIME_GRANTS: Final = tuple(DatabaseGrant(table, ("SELECT",)) for table in RUNTIME_READ_TABLES) + tuple(
    DatabaseGrant(table, ("SELECT", "INSERT") + (("UPDATE",) if table in RUNTIME_UPDATE_TABLES else ()))
    for table in RUNTIME_WRITE_TABLES
)
READONLY_GRANTS: Final = tuple(DatabaseGrant(table, ("SELECT",)) for table in READONLY_PAPER_TABLES)
READONLY_BASELINE_GRANTS: Final = tuple(
    DatabaseGrant(table, ("SELECT",)) for table in READONLY_BASELINE_TABLES
)
READONLY_ACCEPTED_GRANTS: Final = READONLY_BASELINE_GRANTS + READONLY_GRANTS


@dataclass(frozen=True, slots=True)
class PaperPreparationOperationResult:
    changed: bool
    ready: bool = True


class PaperProductionPreparationBackend(Protocol):
    def validate_target(self, target: PaperProductionTargetGuard) -> bool: ...
    def inspect_privilege_drift(self) -> bool: ...
    def inspect_runtime_role(self) -> str: ...
    def ensure_runtime_role(self) -> PaperPreparationOperationResult: ...
    def reconcile_runtime_grants(self) -> PaperPreparationOperationResult: ...
    def reconcile_readonly_grants(self) -> PaperPreparationOperationResult: ...
    def ensure_runtime_binding(self) -> PaperPreparationOperationResult: ...
    def validate_runtime_binding(self) -> bool: ...
    def deploy_disabled_runtime(self) -> PaperPreparationOperationResult: ...
    def deploy_readonly_api_narrow(self) -> PaperPreparationOperationResult: ...
    def action_satisfied(self, action: PaperPreparationAction) -> bool: ...


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationState:
    alembic_revision: str
    phase: PaperPreparationPhase
    schema_ready: bool
    baseline_ready: bool
    runtime_binding_ready: bool
    runtime_role_ready: bool
    runtime_grants_ready: bool
    readonly_paper_grants_ready: bool
    readonly_baseline_grants_ready: bool
    runtime_configuration_ready: bool
    readonly_reporting_deployed: bool
    privilege_drift: bool = False

    @property
    def preparation_complete(self) -> bool:
        return self.phase is PaperPreparationPhase.COMPLETED


@dataclass(frozen=True, slots=True, repr=False)
class PaperProductionPreparationResult:
    planned_actions: tuple[PaperPreparationAction, ...]
    executed_actions: tuple[PaperPreparationAction, ...]
    finding: PaperPreparationFinding
    binding_present: bool
    binding_valid: bool
    role_name: str = PRODUCTION_PAPER_RUNTIME_ROLE
    consumer_health: PaperPreparationConsumerHealth = PaperPreparationConsumerHealth.NOT_CHECKED
    production_mutations: int = 0
    phase: PaperPreparationPhase | None = None

    def __repr__(self) -> str:
        return ("PaperProductionPreparationResult(role_name='traders_paper_runtime', "
                f"finding='{self.finding.value}', binding_present={self.binding_present}, "
                f"binding_valid={self.binding_valid}, production_mutations={self.production_mutations})")

    def safe_dict(self) -> dict[str, object]:
        return {"planned_actions": tuple(x.value for x in self.planned_actions),
                "executed_actions": tuple(x.value for x in self.executed_actions),
                "finding": self.finding.value, "binding_present": self.binding_present,
                "binding_valid": self.binding_valid, "role_name": self.role_name,
                "consumer_health": self.consumer_health.value,
                "production_mutations": self.production_mutations,
                "phase": None if self.phase is None else self.phase.value}


class PaperProductionPreparationExecutor:
    """Preparation-only executor. It has no secret, ARM, START, or trading port."""

    def __init__(self, backend: PaperProductionPreparationBackend) -> None:
        self._backend = backend

    def plan(self, identity: PaperProductionAccountIdentityBinding | None,
             actions: tuple[PaperPreparationAction, ...] = ALL_PREPARATION_ACTIONS) -> PaperProductionPreparationResult:
        finding = PaperPreparationFinding.READY if identity is not None else PaperPreparationFinding.IDENTITY_BINDING_MISSING
        remaining = tuple(action for action in actions if not self._action_satisfied(action))
        return PaperProductionPreparationResult(remaining, (), finding, False, False, production_mutations=0)

    def _action_satisfied(self, action: PaperPreparationAction) -> bool:
        checker = getattr(self._backend, "action_satisfied", None)
        return bool(checker(action)) if checker is not None else False

    def execute(self, identity: PaperProductionAccountIdentityBinding,
                target: PaperProductionTargetGuard,
                budget: PaperProductionPreparationMutationBudget,
                authorization: PaperProductionExecutionAuthorization) -> PaperProductionPreparationResult:
        del identity, budget
        requested_actions = authorization.allowed_actions
        actions = requested_actions
        executed: list[PaperPreparationAction] = []
        mutations = 0
        try:
            if not self._backend.validate_target(target):
                return PaperProductionPreparationResult(actions, (), PaperPreparationFinding.TARGET_ENVIRONMENT_MISMATCH, False, False)
            if self._backend.inspect_privilege_drift():
                return PaperProductionPreparationResult(actions, (), PaperPreparationFinding.EXISTING_ROLE_PRIVILEGE_DRIFT, False, False)
            state = self._backend.inspect_runtime_role()
            if state == "BROADER_THAN_CONTRACT":
                return PaperProductionPreparationResult(actions, (), PaperPreparationFinding.EXISTING_ROLE_PRIVILEGE_DRIFT, False, False)
            actions = tuple(action for action in requested_actions if not self._action_satisfied(action))
            binding_present = False
            binding_valid = False
            operations = {
                PaperPreparationAction.ENSURE_RUNTIME_ROLE: self._backend.ensure_runtime_role,
                PaperPreparationAction.APPLY_RUNTIME_GRANTS: self._backend.reconcile_runtime_grants,
                PaperPreparationAction.APPLY_READONLY_REPORTING_GRANTS: self._backend.reconcile_readonly_grants,
                PaperPreparationAction.BIND_RUNTIME_CREDENTIAL: self._backend.ensure_runtime_binding,
                PaperPreparationAction.DEPLOY_DISABLED_RUNTIME_CONFIGURATION: self._backend.deploy_disabled_runtime,
                PaperPreparationAction.DEPLOY_READONLY_API_NARROW: self._backend.deploy_readonly_api_narrow,
            }
            for action in actions:
                if action is PaperPreparationAction.VALIDATE_RUNTIME_BINDING:
                    binding_valid = self._backend.validate_runtime_binding()
                    binding_present = binding_valid
                    executed.append(action)
                    if not binding_valid:
                        return PaperProductionPreparationResult(actions, tuple(executed),
                            PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING,
                            binding_present, False, production_mutations=mutations)
                    continue
                outcome = operations[action]()
                executed.append(action)
                mutations += int(outcome.changed)
                if action is PaperPreparationAction.BIND_RUNTIME_CREDENTIAL:
                    binding_present = outcome.ready
            return PaperProductionPreparationResult(actions, tuple(executed), PaperPreparationFinding.READY,
                binding_present, binding_valid,
                consumer_health=(PaperPreparationConsumerHealth.HEALTHY if binding_valid
                                 else PaperPreparationConsumerHealth.NOT_CHECKED),
                production_mutations=mutations)
        except Exception:
            raise RuntimeError("PAPER_PRODUCTION_PREPARATION_SAFE_FAILURE") from None


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationReadiness:
    identity_binding_ready: bool
    protected_backend_ready: bool
    runtime_binding_ready: bool
    runtime_grants_ready: bool
    readonly_grants_ready: bool
    schema_ready: bool
    baseline_ready: bool
    readonly_reporting_deployed: bool

    @property
    def findings(self) -> tuple[PaperPreparationFinding, ...]:
        checks = (
            (self.identity_binding_ready, PaperPreparationFinding.IDENTITY_BINDING_MISSING),
            (self.protected_backend_ready, PaperPreparationFinding.PROTECTED_BACKEND_MISSING),
            (self.runtime_binding_ready, PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING),
            (self.runtime_grants_ready, PaperPreparationFinding.RUNTIME_GRANTS_NOT_READY),
            (self.readonly_grants_ready, PaperPreparationFinding.READONLY_GRANTS_NOT_READY),
            (self.schema_ready, PaperPreparationFinding.SCHEMA_NOT_READY),
            (self.baseline_ready, PaperPreparationFinding.BASELINE_MISSING),
            (self.readonly_reporting_deployed, PaperPreparationFinding.READONLY_REPORTING_NOT_DEPLOYED),
        )
        failed = tuple(finding for passed, finding in checks if not passed)
        return failed or (PaperPreparationFinding.READY,)

    @property
    def current_mutation_ready(self) -> bool:
        return self.findings == (PaperPreparationFinding.READY,)


__all__ = [name for name in globals() if name.startswith("Paper") or name in {
    "ALL_PREPARATION_ACTIONS", "EXPECTED_FINAL_ALEMBIC", "EXPECTED_PREVIOUS_ALEMBIC",
    "EXPECTED_START_ALEMBIC", "SUPPORTED_PREPARATION_REVISIONS",
    "IDENTITY_KEYS", "PRODUCTION_PAPER_RUNTIME_ROLE", "PRODUCTION_READONLY_ROLE",
    "READONLY_ACCEPTED_GRANTS", "READONLY_BASELINE_GRANTS", "READONLY_BASELINE_TABLES",
    "READONLY_GRANTS", "READONLY_PAPER_TABLES", "RUNTIME_GRANTS", "RUNTIME_ROLE_POLICY",
}]
