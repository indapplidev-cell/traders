"""Fail-closed contracts for a future production PAPER preparation run.

Nothing in this module discovers a production target or opens a protected
binding.  Callers provide narrow privileged ports; dry-run invokes none of
their mutating or secret-consuming methods.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Callable, Final, Mapping, Protocol

from app.engine_paper.accounting import PaperAccountIdentity


PRODUCTION_PAPER_RUNTIME_ROLE: Final = "traders_paper_runtime"
PRODUCTION_READONLY_ROLE: Final = "traders_readonly_api"
EXPECTED_START_ALEMBIC: Final = "0008_engine_orchestrator_freshness_retry"
EXPECTED_FINAL_ALEMBIC: Final = "0013_paper_first_canary_correlation"
IDENTITY_KEYS: Final = (
    "PAPER_PRODUCTION_ACCOUNT_ID",
    "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID",
    "PAPER_PRODUCTION_CURRENCY",
)
_IDENTIFIER = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,127}$")
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
        missing = tuple(key for key in IDENTITY_KEYS if key not in values)
        if missing:
            raise PaperProductionIdentityError("PRODUCTION_IDENTITY_BINDING_MISSING")
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


class PaperPreparationConsumerHealth(StrEnum):
    NOT_CHECKED = "NOT_CHECKED"
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"


class PaperPreparationFinding(StrEnum):
    READY = "READY"
    IDENTITY_BINDING_MISSING = "IDENTITY_BINDING_MISSING"
    RUNTIME_CREDENTIAL_BINDING_MISSING = "RUNTIME_CREDENTIAL_BINDING_MISSING"
    RUNTIME_GRANTS_NOT_READY = "RUNTIME_GRANTS_NOT_READY"
    READONLY_GRANTS_NOT_READY = "READONLY_GRANTS_NOT_READY"
    SCHEMA_NOT_READY = "SCHEMA_NOT_READY"
    BASELINE_MISSING = "BASELINE_MISSING"
    EXISTING_ROLE_PRIVILEGE_DRIFT = "EXISTING_ROLE_PRIVILEGE_DRIFT"
    TARGET_ENVIRONMENT_MISMATCH = "TARGET_ENVIRONMENT_MISMATCH"
    MUTATION_BUDGET_EXCEEDED = "MUTATION_BUDGET_EXCEEDED"
    SAFE_FAILURE = "SAFE_FAILURE"


@dataclass(frozen=True, slots=True)
class PaperProductionTargetGuard:
    environment: str = "PRODUCTION"
    postgresql_major: int = 16
    expected_start_alembic: str = EXPECTED_START_ALEMBIC

    def __post_init__(self) -> None:
        if (self.environment, self.postgresql_major, self.expected_start_alembic) != (
            "PRODUCTION", 16, EXPECTED_START_ALEMBIC
        ):
            raise ValueError("PRODUCTION_TARGET_GUARD_MISMATCH")


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationMutationBudget:
    max_schema_migration_actions: int = 5
    max_role_create: int = 1
    max_runtime_grant_reconciliation: int = 1
    max_readonly_grant_reconciliation: int = 1
    max_runtime_binding_write: int = 1
    max_baseline_create: int = 1
    max_readonly_api_deployment: int = 1

    def __post_init__(self) -> None:
        if (self.max_schema_migration_actions, self.max_role_create,
                self.max_runtime_grant_reconciliation,
                self.max_readonly_grant_reconciliation,
                self.max_runtime_binding_write, self.max_baseline_create,
                self.max_readonly_api_deployment) != (5, 1, 1, 1, 1, 1, 1):
            raise ValueError("UNBOUNDED_PRODUCTION_PREPARATION_BUDGET")


@dataclass(frozen=True, slots=True)
class DatabaseGrant:
    table: str
    operations: tuple[str, ...]


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
READONLY_PAPER_TABLES: Final = ("paper_account_baselines",) + RUNTIME_WRITE_TABLES
RUNTIME_GRANTS: Final = tuple(
    DatabaseGrant(table, ("SELECT",)) for table in RUNTIME_READ_TABLES
) + tuple(
    DatabaseGrant(table, ("SELECT", "INSERT") + (("UPDATE",) if table in RUNTIME_UPDATE_TABLES else ()))
    for table in RUNTIME_WRITE_TABLES
)
READONLY_GRANTS: Final = tuple(DatabaseGrant(table, ("SELECT",)) for table in READONLY_PAPER_TABLES)


class PaperPreparationPrivilegedBackend(Protocol):
    def inspect_role(self, role_name: str) -> str: ...
    def ensure_login_role(self, role_name: str, password: str, policy: PaperRuntimeRolePolicy) -> bool: ...
    def reconcile_grants(self, role_name: str, grants: tuple[DatabaseGrant, ...]) -> bool: ...
    def validate_binding(self, role_name: str) -> bool: ...
    def deploy_disabled_runtime(self) -> bool: ...
    def deploy_readonly_api_narrow(self) -> bool: ...


class PaperRuntimeProtectedBinding(Protocol):
    def binding_present(self) -> bool: ...
    def store_runtime_credential(self, role_name: str, password: str) -> None: ...


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
                "production_mutations": self.production_mutations}


ALL_PREPARATION_ACTIONS: Final = tuple(PaperPreparationAction)


class PaperProductionPreparationExecutor:
    """Narrow executor with no ARM/START/LIVE/trading vocabulary or capability."""

    def __init__(self, backend: PaperPreparationPrivilegedBackend,
                 protected_binding: PaperRuntimeProtectedBinding,
                 password_factory: Callable[[int], str] = secrets.token_urlsafe) -> None:
        self._backend = backend
        self._binding = protected_binding
        self._password_factory = password_factory

    def plan(self, identity: PaperProductionAccountIdentityBinding | None,
             target: PaperProductionTargetGuard = PaperProductionTargetGuard()) -> PaperProductionPreparationResult:
        del target
        finding = PaperPreparationFinding.READY if identity is not None else PaperPreparationFinding.IDENTITY_BINDING_MISSING
        return PaperProductionPreparationResult(ALL_PREPARATION_ACTIONS, (), finding, False, False, production_mutations=0)

    def execute(self, identity: PaperProductionAccountIdentityBinding,
                target: PaperProductionTargetGuard,
                budget: PaperProductionPreparationMutationBudget) -> PaperProductionPreparationResult:
        del identity, target, budget
        executed: list[PaperPreparationAction] = []
        try:
            state = self._backend.inspect_role(PRODUCTION_PAPER_RUNTIME_ROLE)
            if state == "BROADER_THAN_CONTRACT":
                return PaperProductionPreparationResult(ALL_PREPARATION_ACTIONS, (),
                    PaperPreparationFinding.EXISTING_ROLE_PRIVILEGE_DRIFT, False, False)
            present = self._binding.binding_present()
            password = None
            if state == "ABSENT" or not present:
                password = self._password_factory(48)
                if not isinstance(password, str) or len(password) < 32:
                    raise RuntimeError("SECURE_CREDENTIAL_GENERATION_FAILED")
                self._backend.ensure_login_role(PRODUCTION_PAPER_RUNTIME_ROLE, password, RUNTIME_ROLE_POLICY)
                executed.append(PaperPreparationAction.ENSURE_RUNTIME_ROLE)
                self._binding.store_runtime_credential(PRODUCTION_PAPER_RUNTIME_ROLE, password)
                executed.append(PaperPreparationAction.BIND_RUNTIME_CREDENTIAL)
                password = None
                present = True
            self._backend.reconcile_grants(PRODUCTION_PAPER_RUNTIME_ROLE, RUNTIME_GRANTS)
            executed.append(PaperPreparationAction.APPLY_RUNTIME_GRANTS)
            self._backend.reconcile_grants(PRODUCTION_READONLY_ROLE, READONLY_GRANTS)
            executed.append(PaperPreparationAction.APPLY_READONLY_REPORTING_GRANTS)
            valid = self._backend.validate_binding(PRODUCTION_PAPER_RUNTIME_ROLE)
            executed.append(PaperPreparationAction.VALIDATE_RUNTIME_BINDING)
            if not valid:
                return PaperProductionPreparationResult(ALL_PREPARATION_ACTIONS, tuple(executed),
                    PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING, present, False,
                    production_mutations=len(executed))
            self._backend.deploy_disabled_runtime()
            executed.append(PaperPreparationAction.DEPLOY_DISABLED_RUNTIME_CONFIGURATION)
            self._backend.deploy_readonly_api_narrow()
            executed.append(PaperPreparationAction.DEPLOY_READONLY_API_NARROW)
            return PaperProductionPreparationResult(ALL_PREPARATION_ACTIONS, tuple(executed),
                PaperPreparationFinding.READY, present, True,
                consumer_health=PaperPreparationConsumerHealth.HEALTHY,
                production_mutations=len(executed))
        except Exception as error:
            raise RuntimeError("PAPER_PRODUCTION_PREPARATION_SAFE_FAILURE") from None


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationReadiness:
    identity_binding_ready: bool
    runtime_binding_ready: bool
    runtime_grants_ready: bool
    readonly_grants_ready: bool
    schema_ready: bool
    baseline_ready: bool

    @property
    def findings(self) -> tuple[PaperPreparationFinding, ...]:
        checks = (
            (self.identity_binding_ready, PaperPreparationFinding.IDENTITY_BINDING_MISSING),
            (self.runtime_binding_ready, PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING),
            (self.runtime_grants_ready, PaperPreparationFinding.RUNTIME_GRANTS_NOT_READY),
            (self.readonly_grants_ready, PaperPreparationFinding.READONLY_GRANTS_NOT_READY),
            (self.schema_ready, PaperPreparationFinding.SCHEMA_NOT_READY),
            (self.baseline_ready, PaperPreparationFinding.BASELINE_MISSING),
        )
        failed = tuple(finding for passed, finding in checks if not passed)
        return failed or (PaperPreparationFinding.READY,)

    @property
    def current_mutation_ready(self) -> bool:
        return self.findings == (PaperPreparationFinding.READY,)


__all__ = [name for name in globals() if name.startswith("Paper") or name in {
    "ALL_PREPARATION_ACTIONS", "EXPECTED_FINAL_ALEMBIC", "EXPECTED_START_ALEMBIC",
    "IDENTITY_KEYS", "PRODUCTION_PAPER_RUNTIME_ROLE", "PRODUCTION_READONLY_ROLE",
    "READONLY_GRANTS", "READONLY_PAPER_TABLES", "RUNTIME_GRANTS",
    "RUNTIME_ROLE_POLICY",
}]
