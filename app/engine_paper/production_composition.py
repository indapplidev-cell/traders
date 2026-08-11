"""Disabled-by-default production PAPER composition and preparation contracts.

This module composes already implemented PAPER boundaries.  It deliberately
contains no database target resolver, credential loader, daemon, scheduler, or
automatic migration/arming path.  Production evaluation is read-only and
isolated execution requires an explicitly task-owned target.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Callable, Final, Mapping, Protocol

from app.engine_paper.production_approval import (
    PaperProductionApprovalReadiness,
    PaperProductionApprovalSourceAdapter,
)
from app.engine_paper.production_market_data import (
    PaperProductionMarketDataInputAdapter,
    PaperProductionMarketDataReadiness,
)
from app.engine_safety.paper_production_control import (
    MutationPrerequisites,
    MutationStage,
    PaperProductionMutationAuthorization,
    PaperProductionMutationSafetyGate,
    PaperProductionMutationTarget,
    PersistentState,
)


TASK_ID: Final = "TRADERS_ML_PAPER_TRADING_PRODUCTION_PAPER_PREPARATION_DISABLED_WIRING_01"
EXPECTED_SERVER_BRANCH: Final = "feature/engine-platform"
EXPECTED_SERVER_HEAD: Final = "ff118505a2fe892c7381f9fbb48f2a8530eb22e8"
EXPECTED_SERVER_TREE: Final = "27298c2de1641fa47e4bc3bb8f91c39896323bbe"
EXPECTED_SCHEMA_BASE: Final = "0008_engine_orchestrator_freshness_retry"
EXPECTED_SCHEMA_HEAD: Final = "0011_paper_close_causal_boundary_and_exit_evaluation_cursor"
MINIMUM_PITR_WINDOW_SECONDS: Final = 86_400
PAPER_PRINCIPAL_LOGICAL_NAME: Final = "traders_paper_runtime"

REQUIRED_SOURCE_EVIDENCE_HASHES: Final[Mapping[str, str]] = MappingProxyType({
    "PRODUCTION_MARKET_DATA_INPUT_ADAPTER": "577519b6e7850ef672966fe09b7358b5e3793a6d390425c6e501dc894020647d",
    "PRODUCTION_WAL_ARCHIVE_UNRESOLVED_FAILURE_REMEDIATION": "d63825ee6ed6043ce3b42fe5bda21e7c80578d06c295cb63b55260bb22a1515b",
    "PRODUCTION_APPROVAL_SOURCE_ADAPTER": "6a78c09e9a1ee3e9356198bd6a8521416b1626767704408fb587bfc15ebeee8f",
    "PRODUCTION_KILL_SWITCH_AND_EMERGENCY_STOP": "f519157b39c954f166a3fdb4e2095fe02cb7e1df1f93a54531cf8abd841e6f55",
})


class PaperProductionPreparationReadiness(StrEnum):
    READY_FOR_CONTROLLED_PRODUCTION_PREPARATION = "READY_FOR_CONTROLLED_PRODUCTION_PREPARATION"
    BLOCKED_SCHEMA = "BLOCKED_SCHEMA"
    BLOCKED_PITR = "BLOCKED_PITR"
    BLOCKED_WAL = "BLOCKED_WAL"
    BLOCKED_MARKET_DATA = "BLOCKED_MARKET_DATA"
    BLOCKED_APPROVAL_BOUNDARY = "BLOCKED_APPROVAL_BOUNDARY"
    BLOCKED_PAPER_PRINCIPAL = "BLOCKED_PAPER_PRINCIPAL"
    BLOCKED_RUNTIME_CONFIG = "BLOCKED_RUNTIME_CONFIG"
    BLOCKED_KILL_SWITCH = "BLOCKED_KILL_SWITCH"
    BLOCKED_LIVE_DENIAL = "BLOCKED_LIVE_DENIAL"
    SAFE_FAILURE = "SAFE_FAILURE"


class PaperProductionPreparationGate(StrEnum):
    GIT_BASELINE = "GIT_BASELINE"
    SOURCE_EVIDENCE = "SOURCE_EVIDENCE"
    SECURITY = "SECURITY"
    MARKET_DATA = "MARKET_DATA"
    APPROVAL_BOUNDARY = "APPROVAL_BOUNDARY"
    ELIGIBLE_APPROVAL = "ELIGIBLE_APPROVAL"
    SCHEMA = "SCHEMA"
    PITR = "PITR"
    WAL = "WAL"
    PAPER_PRINCIPAL = "PAPER_PRINCIPAL"
    RUNTIME_CONFIG = "RUNTIME_CONFIG"
    KILL_SWITCH_HEALTH = "KILL_SWITCH_HEALTH"
    KILL_SWITCH_STATE = "KILL_SWITCH_STATE"
    LIVE_DENIAL = "LIVE_DENIAL"


class PaperProductionGateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_DEPLOYED = "NOT_DEPLOYED"
    DISABLED = "DISABLED"


class PaperProductionMutationDecision(StrEnum):
    AUTHORIZED_ONE_ATOMIC_STAGE = "AUTHORIZED_ONE_ATOMIC_STAGE"
    DENIED_FAIL_CLOSED = "DENIED_FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationFinding:
    gate: PaperProductionPreparationGate
    status: PaperProductionGateStatus
    code: str
    mutation_blocking: bool = True


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationTarget:
    environment: str = "PRODUCTION"
    mode: str = "PAPER"
    expected_schema: str = EXPECTED_SCHEMA_HEAD

    def __post_init__(self) -> None:
        if (self.environment, self.mode, self.expected_schema) != (
            "PRODUCTION", "PAPER", EXPECTED_SCHEMA_HEAD
        ):
            raise ValueError("PRODUCTION_PAPER_TARGET_REQUIRED")


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationRequest:
    server_branch: str
    server_head: str
    server_tree: str
    server_clean: bool
    source_evidence_hashes: tuple[tuple[str, str], ...]
    protected_binding_open_count: int
    protected_binding_read_count: int
    protected_binding_hash_count: int
    protected_binding_fingerprint_count: int
    secret_derived_output_count: int
    production_mutation_count: int
    production_paper_table_read_count: int
    schema_revision: str
    pitr_window_seconds: int
    wal_archive_health_pass: bool
    wal_unresolved_failures: int
    pitr_chain_valid: bool
    market_data_readiness: PaperProductionMarketDataReadiness
    approval_boundary_readiness: PaperProductionApprovalReadiness
    eligible_approval_count: int
    paper_principal_ready: bool
    runtime_config_ready: bool
    runtime_enabled: bool
    kill_switch_health_pass: bool
    kill_switch_state: PersistentState
    live_enabled: bool

    def __post_init__(self) -> None:
        counts = (
            self.protected_binding_open_count, self.protected_binding_read_count,
            self.protected_binding_hash_count, self.protected_binding_fingerprint_count,
            self.secret_derived_output_count, self.production_mutation_count,
            self.production_paper_table_read_count, self.pitr_window_seconds,
            self.wal_unresolved_failures, self.eligible_approval_count,
        )
        if any(not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("INVALID_NON_NEGATIVE_COUNTER")


@dataclass(frozen=True, slots=True)
class PaperProductionMutationAuthorizationDecision:
    decision: PaperProductionMutationDecision
    denial_reasons: tuple[str, ...]
    authorized_stage_count: int
    production_mutations: int = 0

    @property
    def authorized(self) -> bool:
        return self.decision is PaperProductionMutationDecision.AUTHORIZED_ONE_ATOMIC_STAGE


@dataclass(frozen=True, slots=True)
class PaperProductionCompositionSnapshot:
    target: PaperProductionPreparationTarget
    preparation_readiness: PaperProductionPreparationReadiness
    findings: tuple[PaperProductionPreparationFinding, ...]
    mutation_authorization: PaperProductionMutationAuthorizationDecision
    reconciliation_precondition: str
    paper_table_reads: int
    production_mutations: int

    def safe_json(self) -> str:
        payload = {
            "target": asdict(self.target),
            "preparation_readiness": self.preparation_readiness.value,
            "findings": [
                {"gate": item.gate.value, "status": item.status.value,
                 "code": item.code, "mutation_blocking": item.mutation_blocking}
                for item in self.findings
            ],
            "mutation_authorization": {
                "decision": self.mutation_authorization.decision.value,
                "denial_reasons": self.mutation_authorization.denial_reasons,
                "authorized_stage_count": self.mutation_authorization.authorized_stage_count,
            },
            "reconciliation_precondition": self.reconciliation_precondition,
            "paper_table_reads": self.paper_table_reads,
            "production_mutations": self.production_mutations,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class PaperProductionPreparationPhase(StrEnum):
    PHASE_1_PRECHECK = "PHASE_1_PRECHECK"
    PHASE_2_CONFIRM_PITR = "PHASE_2_CONFIRM_PITR"
    PHASE_3_MIGRATE_0008_TO_0011 = "PHASE_3_MIGRATE_0008_TO_0011"
    PHASE_4_VERIFY_SCHEMA = "PHASE_4_VERIFY_SCHEMA"
    PHASE_5_CREATE_PAPER_PRINCIPAL = "PHASE_5_CREATE_PAPER_PRINCIPAL"
    PHASE_6_APPLY_LEAST_PRIVILEGE = "PHASE_6_APPLY_LEAST_PRIVILEGE"
    PHASE_7_DEPLOY_DISABLED_RUNTIME_CONFIG = "PHASE_7_DEPLOY_DISABLED_RUNTIME_CONFIG"
    PHASE_8_RECONCILIATION = "PHASE_8_RECONCILIATION"
    PHASE_9_HEALTH = "PHASE_9_HEALTH"
    PHASE_10_CONFIRM_DISABLED = "PHASE_10_CONFIRM_DISABLED"


@dataclass(frozen=True, slots=True)
class PaperProductionMigrationPreflight:
    exact_start_schema: bool
    pitr_pass: bool
    wal_pass: bool
    kill_switch_disabled: bool
    runtime_stopped: bool
    zero_paper_processes: bool
    backup_catalog_valid: bool

    @property
    def passed(self) -> bool:
        return all(asdict(self).values())


@dataclass(frozen=True, slots=True)
class PaperProductionMigrationPostflight:
    exact_final_schema: bool
    reconciliation_pass: bool
    health_pass: bool
    paper_disabled: bool

    @property
    def passed(self) -> bool:
        return all(asdict(self).values())


@dataclass(frozen=True, slots=True)
class PaperProductionMigrationPlan:
    start_revision: str = EXPECTED_SCHEMA_BASE
    revisions: tuple[str, ...] = (
        "0009_paper_trading_persistence_foundation",
        "0010_paper_final_approval_and_order_transition_event_vocabulary",
        EXPECTED_SCHEMA_HEAD,
    )
    lock_timeout_ms: int = 5_000
    statement_timeout_ms: int = 60_000
    automatic_downgrade: bool = False
    failure_policy: str = "STOP_PRESERVE_DB_FORWARD_REMEDIATION_OR_PITR_IF_REQUIRED"

    def __post_init__(self) -> None:
        if self.start_revision != EXPECTED_SCHEMA_BASE or self.revisions[-1] != EXPECTED_SCHEMA_HEAD:
            raise ValueError("UNSUPPORTED_MIGRATION_LINEAGE")
        if self.automatic_downgrade or self.lock_timeout_ms <= 0 or self.statement_timeout_ms <= 0:
            raise ValueError("UNSAFE_MIGRATION_PLAN")


@dataclass(frozen=True, slots=True)
class PaperProductionMigrationPreparation:
    plan: PaperProductionMigrationPlan
    preflight: PaperProductionMigrationPreflight
    execution_target: str
    task_owned_isolated: bool

    @property
    def executable(self) -> bool:
        return self.task_owned_isolated and self.execution_target == "ISOLATED_POSTGRESQL_16" and self.preflight.passed


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationPlan:
    phases: tuple[PaperProductionPreparationPhase, ...] = tuple(PaperProductionPreparationPhase)
    cancellation_between_phases: bool = True
    automatic_continue_after_partial_phase: bool = False
    destructive_rollback: bool = False

    def __post_init__(self) -> None:
        if self.phases != tuple(PaperProductionPreparationPhase):
            raise ValueError("PREPARATION_PHASE_ORDER_MISMATCH")
        if not self.cancellation_between_phases or self.automatic_continue_after_partial_phase or self.destructive_rollback:
            raise ValueError("UNSAFE_PREPARATION_PLAN")


class PaperDatabaseOperation(StrEnum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    ALTER = "ALTER"
    DROP = "DROP"
    CREATE_ROLE = "CREATE_ROLE"
    GRANT = "GRANT"


class PaperProductionPrincipalState(StrEnum):
    NOT_DEPLOYED = "NOT_DEPLOYED"
    EXACT_POLICY = "EXACT_POLICY"
    BROADER_GRANTS = "BROADER_GRANTS"
    CONFLICTING_IDENTITY = "CONFLICTING_IDENTITY"


class PaperProductionIdempotencyAction(StrEnum):
    CREATE_ONCE = "CREATE_ONCE"
    REUSE_EXACT = "REUSE_EXACT"
    CONTINUE = "CONTINUE"
    COMPLETE_NO_ACTION = "COMPLETE_NO_ACTION"
    DENY_CONFLICT = "DENY_CONFLICT"


@dataclass(frozen=True, slots=True)
class PaperProductionPrincipalPreflight:
    state: PaperProductionPrincipalState
    pitr_confirmed: bool
    schema_at_0011: bool
    kill_switch_disabled: bool
    runtime_stopped: bool
    explicit_operator_authorization: bool
    secret_output_count: int = 0

    @property
    def action(self) -> PaperProductionIdempotencyAction:
        if self.secret_output_count or self.state in {
            PaperProductionPrincipalState.BROADER_GRANTS,
            PaperProductionPrincipalState.CONFLICTING_IDENTITY,
        }:
            return PaperProductionIdempotencyAction.DENY_CONFLICT
        if not all((self.pitr_confirmed, self.schema_at_0011,
                    self.kill_switch_disabled, self.runtime_stopped,
                    self.explicit_operator_authorization)):
            return PaperProductionIdempotencyAction.DENY_CONFLICT
        if self.state is PaperProductionPrincipalState.EXACT_POLICY:
            return PaperProductionIdempotencyAction.REUSE_EXACT
        return PaperProductionIdempotencyAction.CREATE_ONCE


@dataclass(frozen=True, slots=True)
class PaperProductionResumeDecision:
    current_schema: str
    principal_state: PaperProductionPrincipalState
    disabled_runtime_config_exact: bool
    reconciliation_healthy: bool

    @property
    def action(self) -> PaperProductionIdempotencyAction:
        if self.current_schema not in {EXPECTED_SCHEMA_BASE, EXPECTED_SCHEMA_HEAD}:
            return PaperProductionIdempotencyAction.DENY_CONFLICT
        if self.principal_state in {PaperProductionPrincipalState.BROADER_GRANTS,
                                    PaperProductionPrincipalState.CONFLICTING_IDENTITY}:
            return PaperProductionIdempotencyAction.DENY_CONFLICT
        if (self.current_schema == EXPECTED_SCHEMA_HEAD
                and self.principal_state is PaperProductionPrincipalState.EXACT_POLICY
                and self.disabled_runtime_config_exact and self.reconciliation_healthy):
            return PaperProductionIdempotencyAction.COMPLETE_NO_ACTION
        return PaperProductionIdempotencyAction.CONTINUE


@dataclass(frozen=True, slots=True)
class PaperProductionDatabaseCapability:
    resource: str
    operation: PaperDatabaseOperation
    required: bool
    reason: str
    runtime_stage: str


_READ_RESOURCES: Final = (
    "alembic_version", "candles_1m", "candles_5m", "candles_15m", "candles_1h", "candles_4h",
    "candles_1d", "market_data_sync_state", "online_pipeline_runs",
    "online_pipeline_results",
)
_PAPER_RESOURCES: Final = (
    "paper_simulation_policies", "paper_execution_commands", "paper_orders",
    "paper_order_events", "paper_fills", "paper_positions",
    "paper_exit_evaluation_cursors", "paper_exit_decisions",
    "paper_journal_entries",
)


def _capability_matrix() -> tuple[PaperProductionDatabaseCapability, ...]:
    rows = [
        PaperProductionDatabaseCapability(resource, PaperDatabaseOperation.SELECT, True,
                                          "existing persisted input or approval boundary", "PRE_MUTATION_READ")
        for resource in _READ_RESOURCES
    ]
    for resource in _PAPER_RESOURCES:
        rows.append(PaperProductionDatabaseCapability(resource, PaperDatabaseOperation.SELECT, True,
                                                       "repository load and reconciliation", "PAPER_LIFECYCLE"))
        rows.append(PaperProductionDatabaseCapability(resource, PaperDatabaseOperation.INSERT, True,
                                                       "repository-owned append or entity creation", "PAPER_LIFECYCLE"))
        if resource in {"paper_execution_commands", "paper_orders", "paper_positions", "paper_exit_evaluation_cursors"}:
            rows.append(PaperProductionDatabaseCapability(resource, PaperDatabaseOperation.UPDATE, True,
                                                           "repository-owned state transition", "PAPER_LIFECYCLE"))
    for resource, operation in (
        ("ALL_TABLES", PaperDatabaseOperation.ALTER),
        ("ALL_TABLES", PaperDatabaseOperation.DROP),
        ("DATABASE_CLUSTER", PaperDatabaseOperation.CREATE_ROLE),
        ("DATABASE_CLUSTER", PaperDatabaseOperation.GRANT),
        ("ml_training_runs", PaperDatabaseOperation.UPDATE),
        ("market_candles", PaperDatabaseOperation.UPDATE),
        ("online_pipeline_runs", PaperDatabaseOperation.UPDATE),
    ):
        rows.append(PaperProductionDatabaseCapability(resource, operation, False,
                                                       "administrative or unrelated business mutation denied", "DENY"))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class PaperProductionDatabasePrincipalPolicy:
    logical_name: str = PAPER_PRINCIPAL_LOGICAL_NAME
    capabilities: tuple[PaperProductionDatabaseCapability, ...] = _capability_matrix()
    schema_admin: bool = False
    role_admin: bool = False
    live_credential_access: bool = False

    def __post_init__(self) -> None:
        if self.logical_name != PAPER_PRINCIPAL_LOGICAL_NAME:
            raise ValueError("PAPER_PRINCIPAL_IDENTITY_MISMATCH")
        if self.schema_admin or self.role_admin or self.live_credential_access:
            raise ValueError("PAPER_PRINCIPAL_EXCESS_PRIVILEGE")
        if len({(row.resource, row.operation) for row in self.capabilities}) != len(self.capabilities):
            raise ValueError("DUPLICATE_CAPABILITY")

    @property
    def fingerprint(self) -> str:
        payload = [(row.resource, row.operation.value, row.required, row.reason, row.runtime_stage)
                   for row in self.capabilities]
        return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeDeploymentConfig:
    mode: str = "PAPER"
    runtime_enabled: bool = False
    daemon_enabled: bool = False
    scheduler_enabled: bool = False
    dry_run: bool = True
    mutation_enabled: bool = False
    live: bool = False
    control_state: PersistentState = PersistentState.DISABLED

    def __post_init__(self) -> None:
        if self.mode != "PAPER" or self.runtime_enabled or self.daemon_enabled or self.scheduler_enabled:
            raise ValueError("RUNTIME_MUST_BE_DEPLOYED_DISABLED")
        if not self.dry_run or self.mutation_enabled or self.live or self.control_state is not PersistentState.DISABLED:
            raise ValueError("UNSAFE_RUNTIME_DEPLOYMENT_CONFIG")


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeTargetIdentity:
    environment: str
    mode: str
    expected_schema: str
    principal_policy_identity: str
    market_data_adapter_identity: str
    approval_adapter_identity: str
    kill_switch_control_identity: str
    runtime_configuration_fingerprint: str

    def __post_init__(self) -> None:
        if (self.environment, self.mode, self.expected_schema) != ("PRODUCTION", "PAPER", EXPECTED_SCHEMA_HEAD):
            raise ValueError("RUNTIME_TARGET_IDENTITY_MISMATCH")
        serialized = json.dumps(asdict(self), sort_keys=True).casefold()
        if "://" in serialized or any(token in serialized for token in ("password", "credential", "database_url")):
            raise ValueError("SECRET_SHAPED_TARGET_IDENTITY_DENIED")


def runtime_configuration_fingerprint(config: PaperProductionRuntimeDeploymentConfig) -> str:
    return hashlib.sha256(json.dumps({**asdict(config), "control_state": config.control_state.value},
                                     sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PaperProductionDeploymentPlan:
    config: PaperProductionRuntimeDeploymentConfig = PaperProductionRuntimeDeploymentConfig()
    publish_budget: int = 1
    automatic_start: bool = False
    automatic_arm: bool = False

    def __post_init__(self) -> None:
        if self.publish_budget != 1 or self.automatic_start or self.automatic_arm:
            raise ValueError("UNSAFE_DEPLOYMENT_PLAN")


@dataclass(frozen=True, slots=True)
class PaperProductionFirstCanaryPlan:
    environment: str = "PRODUCTION"
    mode: str = "PAPER"
    max_commands: int = 1
    max_open_positions: int = 1
    allowed_symbols: tuple[str, ...] = ("BTCUSDT",)
    binance_order_calls: int = 0
    simulated_execution_only: bool = True
    explicit_operator_arm_required: bool = True
    bounded_lifecycle: bool = True
    kill_switch_checked_every_stage: bool = True
    reconciliation_after_canary: bool = True
    no_eligible_approval_behavior: str = "NO_ELIGIBLE_APPROVAL_ZERO_MUTATION_CLEAN_NO_TRADE"

    def __post_init__(self) -> None:
        if (self.environment, self.mode, self.max_commands, self.max_open_positions) != ("PRODUCTION", "PAPER", 1, 1):
            raise ValueError("CANARY_NOT_MINIMAL")
        if not self.allowed_symbols or self.binance_order_calls != 0 or not all((
            self.simulated_execution_only, self.explicit_operator_arm_required,
            self.bounded_lifecycle, self.kill_switch_checked_every_stage,
            self.reconciliation_after_canary,
        )):
            raise ValueError("UNSAFE_FIRST_CANARY_PLAN")


@dataclass(frozen=True, slots=True)
class PaperProductionMutationBudget:
    schema_migrations: tuple[str, ...] = PaperProductionMigrationPlan().revisions
    principal_creations: int = 1
    disabled_runtime_publications: int = 1
    paper_business_rows: int = 0
    paper_commands: int = 0
    paper_orders: int = 0
    paper_fills: int = 0
    paper_positions: int = 0


OBSERVABILITY_EVENTS: Final = (
    "runtime_canary_start", "runtime_canary_finish", "safety_gate_state",
    "approval_outcome", "command_creation", "order_creation", "fill",
    "position_open", "position_close", "exit_decision", "fault_error",
    "reconciliation_result", "kill_switch_emergency_stop",
)


def safe_structured_event(event: str, fields: Mapping[str, object]) -> str:
    if event not in OBSERVABILITY_EVENTS:
        raise ValueError("OBSERVABILITY_EVENT_NOT_ALLOWLISTED")
    forbidden = ("password", "secret", "credential", "database_url", "dsn", "binding", "environment")
    keys = " ".join(map(str, fields)).casefold()
    rendered = json.dumps(dict(fields), sort_keys=True, separators=(",", ":"), default=str)
    if any(token in keys for token in forbidden) or "://" in rendered:
        raise ValueError("SECRET_SHAPED_LOG_FIELD_DENIED")
    return json.dumps({"event": event, "fields": dict(fields)}, sort_keys=True,
                      separators=(",", ":"), default=str)


def _schema_finding(revision: str) -> PaperProductionPreparationFinding:
    if revision == EXPECTED_SCHEMA_HEAD:
        return PaperProductionPreparationFinding(PaperProductionPreparationGate.SCHEMA,
                                                  PaperProductionGateStatus.PASS, "SCHEMA_0011")
    if revision == EXPECTED_SCHEMA_BASE:
        code = "SCHEMA_0008"
    elif revision in {"0009_paper_trading_persistence_foundation",
                      "0010_paper_final_approval_and_order_transition_event_vocabulary"}:
        code = "SCHEMA_PARTIAL_FAIL_CLOSED"
    else:
        code = "SCHEMA_UNEXPECTED_COMPATIBILITY_REVIEW_REQUIRED"
    return PaperProductionPreparationFinding(PaperProductionPreparationGate.SCHEMA,
                                              PaperProductionGateStatus.FAIL, code)


class PaperProductionComposition:
    """Binds production adapters and the mandatory per-stage safety gate."""

    def __init__(self, market_data_adapter: PaperProductionMarketDataInputAdapter,
                 approval_source_adapter: PaperProductionApprovalSourceAdapter,
                 mutation_safety_gate: PaperProductionMutationSafetyGate) -> None:
        if not isinstance(market_data_adapter, PaperProductionMarketDataInputAdapter):
            raise TypeError("PRODUCTION_MARKET_DATA_ADAPTER_REQUIRED")
        if not isinstance(approval_source_adapter, PaperProductionApprovalSourceAdapter):
            raise TypeError("PRODUCTION_APPROVAL_ADAPTER_REQUIRED")
        if not isinstance(mutation_safety_gate, PaperProductionMutationSafetyGate):
            raise TypeError("PRODUCTION_MUTATION_SAFETY_GATE_REQUIRED")
        self.market_data_adapter = market_data_adapter
        self.approval_source_adapter = approval_source_adapter
        self.mutation_safety_gate = mutation_safety_gate

    @staticmethod
    def evaluate(request: PaperProductionPreparationRequest) -> PaperProductionCompositionSnapshot:
        expected_evidence = tuple(REQUIRED_SOURCE_EVIDENCE_HASHES.items())
        baseline_pass = (request.server_branch, request.server_head, request.server_tree, request.server_clean) == (
            EXPECTED_SERVER_BRANCH, EXPECTED_SERVER_HEAD, EXPECTED_SERVER_TREE, True)
        evidence_pass = request.source_evidence_hashes == expected_evidence
        security_pass = not any((request.protected_binding_open_count,
                                 request.protected_binding_read_count,
                                 request.protected_binding_hash_count,
                                 request.protected_binding_fingerprint_count,
                                 request.secret_derived_output_count))
        market_pass = request.market_data_readiness is PaperProductionMarketDataReadiness.READY
        approval_pass = request.approval_boundary_readiness in {
            PaperProductionApprovalReadiness.READY,
            PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL,
        }
        findings = [
            PaperProductionPreparationFinding(PaperProductionPreparationGate.GIT_BASELINE,
                PaperProductionGateStatus.PASS if baseline_pass else PaperProductionGateStatus.FAIL,
                "GIT_BASELINE_EXACT" if baseline_pass else "GIT_BASELINE_MISMATCH"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.SOURCE_EVIDENCE,
                PaperProductionGateStatus.PASS if evidence_pass else PaperProductionGateStatus.FAIL,
                "SOURCE_EVIDENCE_HASHES_MATCH" if evidence_pass else "BLOCKED_SOURCE_EVIDENCE_HASH_MISMATCH"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.SECURITY,
                PaperProductionGateStatus.PASS if security_pass else PaperProductionGateStatus.FAIL,
                "SECURITY_ZERO_BINDING" if security_pass else "SECURITY_INVARIANT_VIOLATED"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.MARKET_DATA,
                PaperProductionGateStatus.PASS if market_pass else PaperProductionGateStatus.FAIL,
                "MARKET_DATA_READY" if market_pass else "MARKET_DATA_NOT_READY"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.APPROVAL_BOUNDARY,
                PaperProductionGateStatus.PASS if approval_pass else PaperProductionGateStatus.FAIL,
                "APPROVAL_BOUNDARY_READY" if approval_pass else "APPROVAL_BOUNDARY_NOT_READY"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.ELIGIBLE_APPROVAL,
                PaperProductionGateStatus.PASS if request.eligible_approval_count == 1 else PaperProductionGateStatus.FAIL,
                "ELIGIBLE_APPROVAL_PRESENT" if request.eligible_approval_count == 1 else "NO_ELIGIBLE_APPROVAL"),
            _schema_finding(request.schema_revision),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.PITR,
                PaperProductionGateStatus.PASS if request.pitr_window_seconds >= MINIMUM_PITR_WINDOW_SECONDS else PaperProductionGateStatus.FAIL,
                "PITR_AT_LEAST_24H" if request.pitr_window_seconds >= MINIMUM_PITR_WINDOW_SECONDS else "PITR_BELOW_24H"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.WAL,
                PaperProductionGateStatus.PASS if request.wal_archive_health_pass and request.wal_unresolved_failures == 0 and request.pitr_chain_valid else PaperProductionGateStatus.FAIL,
                "WAL_HEALTH_PASS" if request.wal_archive_health_pass and request.wal_unresolved_failures == 0 and request.pitr_chain_valid else "WAL_GATE_FAILED"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.PAPER_PRINCIPAL,
                PaperProductionGateStatus.PASS if request.paper_principal_ready else PaperProductionGateStatus.NOT_DEPLOYED,
                "PAPER_PRINCIPAL_READY" if request.paper_principal_ready else "PAPER_PRINCIPAL_NOT_DEPLOYED"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.RUNTIME_CONFIG,
                PaperProductionGateStatus.PASS if request.runtime_config_ready and request.runtime_enabled else PaperProductionGateStatus.DISABLED,
                "PAPER_RUNTIME_READY" if request.runtime_config_ready and request.runtime_enabled else "PAPER_RUNTIME_DISABLED"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.KILL_SWITCH_HEALTH,
                PaperProductionGateStatus.PASS if request.kill_switch_health_pass else PaperProductionGateStatus.FAIL,
                "KILL_SWITCH_HEALTHY" if request.kill_switch_health_pass else "KILL_SWITCH_UNHEALTHY"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.KILL_SWITCH_STATE,
                PaperProductionGateStatus.PASS if request.kill_switch_state is PersistentState.ARMED else PaperProductionGateStatus.DISABLED,
                "CONTROL_STATE_ARMED" if request.kill_switch_state is PersistentState.ARMED else f"CONTROL_STATE_{request.kill_switch_state.value}"),
            PaperProductionPreparationFinding(PaperProductionPreparationGate.LIVE_DENIAL,
                PaperProductionGateStatus.PASS if not request.live_enabled else PaperProductionGateStatus.FAIL,
                "LIVE_DENIED" if not request.live_enabled else "LIVE_NOT_DENIED"),
        ]
        primary_reason_gates = (
            PaperProductionPreparationGate.SCHEMA,
            PaperProductionPreparationGate.PITR,
            PaperProductionPreparationGate.RUNTIME_CONFIG,
            PaperProductionPreparationGate.KILL_SWITCH_STATE,
        )
        primary_reasons = tuple(
            item.code for gate in primary_reason_gates for item in findings
            if item.gate is gate and item.status is not PaperProductionGateStatus.PASS
        )
        # Give operators the stable root blockers first.  Once those close, the
        # remaining conjunction (including principal and eligible approval)
        # becomes visible; no failed gate can authorize a mutation.
        reasons = primary_reasons or tuple(
            item.code for item in findings if item.status is not PaperProductionGateStatus.PASS
        )
        authorized = not any(item.status is not PaperProductionGateStatus.PASS for item in findings)
        decision = PaperProductionMutationAuthorizationDecision(
            PaperProductionMutationDecision.AUTHORIZED_ONE_ATOMIC_STAGE if authorized else PaperProductionMutationDecision.DENIED_FAIL_CLOSED,
            () if authorized else reasons, 1 if authorized else 0, request.production_mutation_count,
        )
        hard_preparation_failure = not all((baseline_pass, evidence_pass, security_pass,
                                            market_pass, approval_pass,
                                            request.production_mutation_count == 0,
                                            request.production_paper_table_read_count == 0))
        readiness = (PaperProductionPreparationReadiness.SAFE_FAILURE if hard_preparation_failure else
                     PaperProductionPreparationReadiness.READY_FOR_CONTROLLED_PRODUCTION_PREPARATION)
        return PaperProductionCompositionSnapshot(
            PaperProductionPreparationTarget(), readiness, tuple(findings), decision,
            "READY" if request.schema_revision == EXPECTED_SCHEMA_HEAD else "PAPER_SCHEMA_NOT_DEPLOYED",
            request.production_paper_table_read_count, request.production_mutation_count,
        )

    def authorize_stage(self, stage: MutationStage, target: PaperProductionMutationTarget,
                        prerequisites: MutationPrerequisites,
                        transaction: Callable[[], object]) -> object:
        with self.mutation_safety_gate.authorize_mutation(stage, target, prerequisites):
            return transaction()


@dataclass(frozen=True, slots=True)
class PaperProductionIsolatedMigrationResult:
    completed_revisions: tuple[str, ...]
    final_revision: str
    duration_ms: int
    lock_waits: int
    statement_timeouts: int
    postflight: PaperProductionMigrationPostflight
    stopped: bool
    failure_code: str | None = None


class PaperProductionIsolatedMigrationExecutor(Protocol):
    def apply(self, revision: str, lock_timeout_ms: int, statement_timeout_ms: int) -> None: ...
    def current_revision(self) -> str: ...
    def reconcile(self) -> bool: ...
    def health(self) -> bool: ...


class PaperProductionMigrationOrchestrator:
    """Bounded isolated rehearsal runner; production execution is impossible here."""

    def run_isolated(self, preparation: PaperProductionMigrationPreparation,
                     executor: PaperProductionIsolatedMigrationExecutor,
                     cancelled: Callable[[], bool] = lambda: False) -> PaperProductionIsolatedMigrationResult:
        if not preparation.executable:
            raise RuntimeError("MIGRATION_PREFLIGHT_OR_TARGET_DENIED")
        completed: list[str] = []
        try:
            if executor.current_revision() != preparation.plan.start_revision:
                raise RuntimeError("BASELINE_SCHEMA_MISMATCH")
            for revision in preparation.plan.revisions:
                if cancelled():
                    return PaperProductionIsolatedMigrationResult(tuple(completed), executor.current_revision(), 0, 0, 0,
                        PaperProductionMigrationPostflight(False, False, False, True), True, "CANCELLED_BETWEEN_PHASES")
                executor.apply(revision, preparation.plan.lock_timeout_ms, preparation.plan.statement_timeout_ms)
                completed.append(revision)
            final_revision = executor.current_revision()
            postflight = PaperProductionMigrationPostflight(
                final_revision == EXPECTED_SCHEMA_HEAD, executor.reconcile(), executor.health(), True)
            if not postflight.passed:
                return PaperProductionIsolatedMigrationResult(tuple(completed), final_revision, 0, 0, 0,
                                                               postflight, True, "POSTFLIGHT_FAILED")
            return PaperProductionIsolatedMigrationResult(tuple(completed), final_revision, 0, 0, 0,
                                                           postflight, False)
        except Exception as error:
            return PaperProductionIsolatedMigrationResult(tuple(completed), executor.current_revision(), 0, 0, 0,
                PaperProductionMigrationPostflight(False, False, False, True), True, type(error).__name__.upper())


__all__ = [name for name in globals() if name.startswith("Paper") or name in {
    "EXPECTED_SCHEMA_BASE", "EXPECTED_SCHEMA_HEAD", "MINIMUM_PITR_WINDOW_SECONDS",
    "OBSERVABILITY_EVENTS", "REQUIRED_SOURCE_EVIDENCE_HASHES",
    "runtime_configuration_fingerprint", "safe_structured_event",
}]
