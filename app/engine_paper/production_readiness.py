"""Pure, review-only contracts for future production PAPER readiness.

Nothing in this module can enable a target, resolve a database binding, execute
a runner, or mutate a database.  It records bounded evidence and applies a
fail-closed readiness decision to a separately executed review.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Mapping


TASK_ID: Final = (
    "TRADERS_ML_PAPER_TRADING_PRODUCTION_PAPER_RUNTIME_READINESS_REVIEW_01"
)
EXPECTED_SERVER_BRANCH: Final = "feature/engine-platform"
EXPECTED_SERVER_HEAD: Final = "0988984b9d37ab22e811ba106ae19c068d374438"
EXPECTED_SERVER_TREE: Final = "d423e5ce44c19245ed8161a9e0505c4090103057"
EXPECTED_SCHEMA_BASE: Final = "0008_engine_orchestrator_freshness_retry"
EXPECTED_SCHEMA_HEAD: Final = (
    "0012_paper_account_baseline"
)
MAX_SAFE_RENDER_BYTES: Final = 65_536
MAX_EVIDENCE_ITEMS: Final = 32
MAX_BLOCKERS_PER_DOMAIN: Final = 8
MAX_TEXT_LENGTH: Final = 512


EXPECTED_EVIDENCE_HASHES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "FOUNDATION_PREPARATION": "0b430bcc838eeffa7f6044425884ea1420ea3497bb8ecc994ba4e6be9dc5a8bb",
        "DOMAIN_AND_STATE_MACHINE": "cdb435175ef28d5a3f83dd80f8b25a2e8fdc53c482148e1024a2ae23f50e0b1b",
        "PERSISTENCE_SCHEMA": "823536365958424349da8085660093c285e1dcd94471f10358d18f43f4af22ef",
        "REPOSITORY_AND_IDEMPOTENCY": "e4230d9d15bb3f62a49a7195d3a92f03b07fe7d44a0370f78f2b7f9573793e9d",
        "DETERMINISTIC_FILL_SIMULATOR": "db00f888b92e142eae30d1a8163ee0169deef3546fb6d456f50d6eb998c78328",
        "ORDER_EXECUTION_SERVICE": "57848a81be3c18eadd86e95e438b3bc4ede3869d3db9b0908ba9f7a460e81339",
        "FINAL_APPROVAL_AND_EVENT_REMEDIATION": "91d4bcff673ca53a2b21de81a507fb4befcac5587aeca775bdffeae5f117187d",
        "COMMAND_INGESTION_RETRY": "f217e8b7b5c8821be1130da7b923784b938f4abc4f623b7e621e5716ad1f614e",
        "CLOSE_CAUSAL_AND_CURSOR_REMEDIATION": "f3e43ce5c57691771624be5e61f11c41476c1e15d932f21a2c83a8db5c9af3c1",
        "EXIT_EVALUATION_RETRY": "5b33f878d60dd564e143463bdadcf8f5ff3e6b5b541cb3006075574ba42e849a",
        "ENTRY_CURSOR_INITIALIZATION_RETRY": "bde21a3794bf5dc008a0c041f201c0b433fd52fea3d4f352a363d72a4ec14f16",
        "CONTROLLED_WORKER_RETRY": "1434340044d248d1832ca3752a235d3de7113f3cf02c282c1936034cdad8c037",
        "CONTROLLED_RUNTIME_CONFIGURATION_AND_DRY_RUN": "287b46c1018aac8315817d1ac876a894bbe4fa695fd64bc7f5e729c16f91db73",
        "FAILED_SINGLE_CYCLE_CANARY": "dbd41caa1a338ef9689453e75cb8bf07c53ecc8942bc41d3349687bb1ba99c23",
        "BLOCKED_SECURITY_ATTEMPT": "be9897866fb26bee73f5db5b84caea2011ddaeeaa812f68ad62c5a0a44454753",
        "SECURITY_REMEDIATION_RETRY": "afce8eae9d58135a3d9d1e5591cbb0ede5546a90030a9885fb9427d4e6edeaa0",
        "BLOCKED_CANARY_RETRY_01": "64496b15a3dc33157ae4a1bd230154368d0254c5ce164abff061974516c59900",
        "SINGLE_CYCLE_CANARY_RETRY_02": "c9ef780f6c16e1a06564d4b879c416df609821dae9ccf141949bceefa44b22b4",
        "BOUNDED_SEQUENCE_CANARY": "d97cab0ec98de5cbab640da5548789efbd5a3bc4f8335cc2b51e4f9ed1618776",
        "OPERATOR_CONTROLLED_RUNNER": "18e7b78381c0bc0de043c96c870c35ebbcb7cfb665f233bd1d5a23d6fee517db",
    }
)


class PaperProductionRuntimeReadinessDomain(StrEnum):
    R1_SCHEMA_MIGRATION = "R1_SCHEMA_MIGRATION"
    R2_ROLLBACK_FORWARD_FIX = "R2_ROLLBACK_FORWARD_FIX"
    R3_DEPLOYMENT_TOPOLOGY = "R3_DEPLOYMENT_TOPOLOGY"
    R4_OPERATOR_AUTHORIZATION = "R4_OPERATOR_AUTHORIZATION"
    R5_TARGET_ISOLATION_PERMISSIONS = "R5_TARGET_ISOLATION_PERMISSIONS"
    R6_MARKET_DATA_INPUT = "R6_MARKET_DATA_INPUT"
    R7_EXECUTION_BOUNDS_STOP_CONTROLS = "R7_EXECUTION_BOUNDS_STOP_CONTROLS"
    R8_IDEMPOTENCY_REPLAY_CONCURRENCY = "R8_IDEMPOTENCY_REPLAY_CONCURRENCY"
    R9_OBSERVABILITY_ALERTING = "R9_OBSERVABILITY_ALERTING"
    R10_INCIDENT_EMERGENCY_STOP = "R10_INCIDENT_EMERGENCY_STOP"
    R11_DATA_RETENTION_CLEANUP = "R11_DATA_RETENTION_CLEANUP"
    R12_BACKUP_RECOVERY_RECONCILIATION = "R12_BACKUP_RECOVERY_RECONCILIATION"
    R13_PERFORMANCE_CAPACITY = "R13_PERFORMANCE_CAPACITY"
    R14_API_CLIENT_EXPOSURE = "R14_API_CLIENT_EXPOSURE"
    R15_SECURITY_SECRET_HANDLING = "R15_SECURITY_SECRET_HANDLING"
    R16_RELEASE_ROLLBACK_PROCEDURE = "R16_RELEASE_ROLLBACK_PROCEDURE"
    R17_POST_ENABLE_VALIDATION = "R17_POST_ENABLE_VALIDATION"
    R18_LIVE_SEPARATION = "R18_LIVE_SEPARATION"


class ReadinessStatus(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNPROVEN = "UNPROVEN"


class FindingSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class MigrationClassification(StrEnum):
    ONLINE_SAFE = "ONLINE_SAFE"
    REQUIRES_MAINTENANCE_WINDOW = "REQUIRES_MAINTENANCE_WINDOW"
    REQUIRES_WRITE_QUIESCE = "REQUIRES_WRITE_QUIESCE"
    REQUIRES_PRE_BACKUP = "REQUIRES_PRE_BACKUP"
    REQUIRES_FORWARD_FIX_ONLY = "REQUIRES_FORWARD_FIX_ONLY"
    BLOCKED = "BLOCKED"


class DowngradeClassification(StrEnum):
    FULL_DOWNGRADE_SUPPORTED = "FULL_DOWNGRADE_SUPPORTED"
    SCHEMA_DOWNGRADE_ONLY = "SCHEMA_DOWNGRADE_ONLY"
    DOWNGRADE_DESTRUCTIVE = "DOWNGRADE_DESTRUCTIVE"
    DOWNGRADE_UNSUPPORTED = "DOWNGRADE_UNSUPPORTED"
    FORWARD_FIX_REQUIRED = "FORWARD_FIX_REQUIRED"


class ProductionPaperRuntimeReadiness(StrEnum):
    READY = "READY_FOR_SEPARATE_CONTROLLED_ENABLEMENT_TASK"
    NOT_READY = "NOT_READY_BLOCKERS_IDENTIFIED"


def _bounded_text(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT_LENGTH:
        raise ValueError("INVALID_BOUNDED_TEXT")
    if any(ord(character) < 32 for character in value):
        raise ValueError("INVALID_BOUNDED_TEXT")
    return value


def _bounded_tuple(values: tuple[str, ...], maximum: int = MAX_EVIDENCE_ITEMS) -> None:
    if not isinstance(values, tuple) or not 1 <= len(values) <= maximum:
        raise ValueError("INVALID_BOUNDED_COLLECTION")
    for value in values:
        _bounded_text(value)


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeReadinessBlocker:
    code: str
    severity: FindingSeverity
    description: str
    remediation_task: str

    def __post_init__(self) -> None:
        _bounded_text(self.code)
        _bounded_text(self.description)
        _bounded_text(self.remediation_task)


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeReadinessFinding:
    domain: PaperProductionRuntimeReadinessDomain
    status: ReadinessStatus
    evidence: tuple[str, ...]
    blockers: tuple[PaperProductionRuntimeReadinessBlocker, ...]
    required_followup: str
    enablement_gate: str

    def __post_init__(self) -> None:
        _bounded_tuple(self.evidence)
        if len(self.blockers) > MAX_BLOCKERS_PER_DOMAIN:
            raise ValueError("TOO_MANY_BLOCKERS")
        _bounded_text(self.required_followup)
        _bounded_text(self.enablement_gate)
        if self.status is ReadinessStatus.READY and self.blockers:
            raise ValueError("READY_DOMAIN_HAS_BLOCKERS")
        if self.status in (ReadinessStatus.NOT_READY, ReadinessStatus.UNPROVEN) and not self.blockers:
            raise ValueError("NON_READY_DOMAIN_REQUIRES_BLOCKER")


@dataclass(frozen=True, slots=True)
class PaperProductionMigrationManifest:
    revision: str
    predecessor: str
    classification: MigrationClassification
    ddl_operations: tuple[str, ...]
    locking_characteristics: str
    transaction_behavior: str
    expected_duration: str
    dependency_ordering: str
    forward_only_assumptions: str
    downgrade_support: DowngradeClassification
    data_backfill: str
    default_nullability: str
    runtime_compatibility: str
    source_sha256: str

    def __post_init__(self) -> None:
        for value in (
            self.revision,
            self.predecessor,
            self.locking_characteristics,
            self.transaction_behavior,
            self.expected_duration,
            self.dependency_ordering,
            self.forward_only_assumptions,
            self.data_backfill,
            self.default_nullability,
            self.runtime_compatibility,
            self.source_sha256,
        ):
            _bounded_text(value)
        _bounded_tuple(self.ddl_operations)


MIGRATION_MANIFESTS: Final = (
    PaperProductionMigrationManifest(
        revision="0009_paper_trading_persistence_foundation",
        predecessor=EXPECTED_SCHEMA_BASE,
        classification=MigrationClassification.REQUIRES_PRE_BACKUP,
        ddl_operations=(
            "CREATE 8 PAPER tables",
            "CREATE 10 PAPER indexes",
            "CREATE primary unique foreign-key and check constraints",
        ),
        locking_characteristics="ACCESS EXCLUSIVE per CREATE TABLE and catalog/index locks; new empty tables avoid existing-row rewrite",
        transaction_behavior="single transactional Alembic revision on PostgreSQL",
        expected_duration="short on production shape because all objects are new and no data backfill occurs",
        dependency_ordering="policy and command before orders; orders before fills and positions; causal rows before journal",
        forward_only_assumptions="existing 0008 services do not reference PAPER tables",
        downgrade_support=DowngradeClassification.DOWNGRADE_DESTRUCTIVE,
        data_backfill="none",
        default_nullability="one PENDING server default; remaining required fields supplied on insert",
        runtime_compatibility="0008 market-data orchestrator and readonly API remain compatible before and after",
        source_sha256="8cbb1e2b580c9494b3b0da7beb5a6484e8de202d6e3936873f293456bb934254",
    ),
    PaperProductionMigrationManifest(
        revision="0010_paper_final_approval_and_order_transition_event_vocabulary",
        predecessor="0009_paper_trading_persistence_foundation",
        classification=MigrationClassification.REQUIRES_WRITE_QUIESCE,
        ddl_operations=("REPLACE 2 CHECK constraints to extend event vocabulary",),
        locking_characteristics="ACCESS EXCLUSIVE while each CHECK constraint is replaced and existing rows are validated",
        transaction_behavior="single transactional Alembic revision on PostgreSQL",
        expected_duration="bounded by validation scan of paper_order_events and paper_journal_entries",
        dependency_ordering="requires 0009 event and journal tables",
        forward_only_assumptions="no concurrent PAPER writes during constraint replacement",
        downgrade_support=DowngradeClassification.SCHEMA_DOWNGRADE_ONLY,
        data_backfill="none",
        default_nullability="unchanged",
        runtime_compatibility="existing non-PAPER services unaffected; 0010 writers require extended vocabulary",
        source_sha256="1b84e106162a374fef781b71ed2f40d81a76a0cd352a8179aef10402219e8b55",
    ),
    PaperProductionMigrationManifest(
        revision="0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
        predecessor="0010_paper_final_approval_and_order_transition_event_vocabulary",
        classification=MigrationClassification.REQUIRES_PRE_BACKUP,
        ddl_operations=(
            "CREATE paper_exit_evaluation_cursors table",
            "CREATE 1 cursor progression index",
            "CREATE position foreign key and cursor invariants",
        ),
        locking_characteristics="catalog and referenced-table foreign-key locks; new empty table avoids row rewrite",
        transaction_behavior="single transactional Alembic revision on PostgreSQL",
        expected_duration="short on production shape because the table and index are initially empty",
        dependency_ordering="requires 0010 paper_positions",
        forward_only_assumptions="new successful ENTRY execution requires cursor table after deployment",
        downgrade_support=DowngradeClassification.DOWNGRADE_DESTRUCTIVE,
        data_backfill="none; production has no PAPER rows before enablement",
        default_nullability="all required cursor fields non-null; last-advance group nullable as an all-or-none set",
        runtime_compatibility="0008 services unaffected; cursor-aware PAPER runtime requires 0011 or later",
        source_sha256="01e011e457a33b61f76ae413b18a23e4a9787a2920dbdbefe9c48a0553287b49",
    ),
    PaperProductionMigrationManifest(
        revision=EXPECTED_SCHEMA_HEAD,
        predecessor="0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
        classification=MigrationClassification.REQUIRES_PRE_BACKUP,
        ddl_operations=(
            "CREATE paper_account_baselines table",
            "CREATE primary unique and immutable-value check constraints",
        ),
        locking_characteristics="catalog locks for one new empty table; no existing PAPER row rewrite",
        transaction_behavior="single transactional Alembic revision on PostgreSQL",
        expected_duration="short because the baseline table is created empty",
        dependency_ordering="requires the complete 0011 PAPER economic graph",
        forward_only_assumptions="operator supplies initial balance only after migration and before first command",
        downgrade_support=DowngradeClassification.DOWNGRADE_DESTRUCTIVE,
        data_backfill="none; no fake or default baseline is seeded",
        default_nullability="all baseline identity value timestamp and semantic fields are non-null",
        runtime_compatibility="0008 services unaffected; current PAPER runtime and accounting require 0012 exactly",
        source_sha256="9acf623e1c1b64fb51658a95e5f4cddac6999e0b1f2ada5d9b2428cd527e881e",
    ),
)


@dataclass(frozen=True, slots=True)
class PaperProductionMigrationRehearsalResult:
    passed: bool
    start_revision: str
    final_revision: str
    duration_ms: int
    maximum_lock_wait_ms: int
    unexpected_destructive_ddl: int
    compatibility_checks_passed: bool
    paper_smoke_passed: bool
    open_connections_before_cleanup: int
    idle_transactions_before_cleanup: int
    lock_waits_before_cleanup: int
    container_removed: bool
    artifacts_cleaned: bool

    def __post_init__(self) -> None:
        if self.duration_ms < 0 or self.maximum_lock_wait_ms < 0:
            raise ValueError("NEGATIVE_REHEARSAL_METRIC")
        for value in (
            self.unexpected_destructive_ddl,
            self.open_connections_before_cleanup,
            self.idle_transactions_before_cleanup,
            self.lock_waits_before_cleanup,
        ):
            if value < 0:
                raise ValueError("NEGATIVE_REHEARSAL_COUNT")

    @property
    def accepted(self) -> bool:
        return (
            self.passed
            and self.start_revision == EXPECTED_SCHEMA_BASE
            and self.final_revision == EXPECTED_SCHEMA_HEAD
            and self.unexpected_destructive_ddl == 0
            and self.compatibility_checks_passed
            and self.paper_smoke_passed
            and self.open_connections_before_cleanup == 0
            and self.idle_transactions_before_cleanup == 0
            and self.lock_waits_before_cleanup == 0
            and self.container_removed
            and self.artifacts_cleaned
        )


@dataclass(frozen=True, slots=True)
class PaperProductionRollbackStrategy:
    classification: DowngradeClassification
    strategy: str
    paper_data_loss_on_downgrade: bool
    preconditions: tuple[str, ...]
    validation: tuple[str, ...]

    def __post_init__(self) -> None:
        _bounded_text(self.strategy)
        _bounded_tuple(self.preconditions)
        _bounded_tuple(self.validation)


ROLLBACK_STRATEGY: Final = PaperProductionRollbackStrategy(
    classification=DowngradeClassification.DOWNGRADE_DESTRUCTIVE,
    strategy="APPLICATION_DISABLE_PLUS_FORWARD_FIX",
    paper_data_loss_on_downgrade=True,
    preconditions=(
        "deny new PAPER commands and wait for active child transaction completion",
        "capture approved database backup and durable PAPER reconciliation manifest",
        "retain 0012 schema while application is disabled unless destructive loss is accepted",
    ),
    validation=(
        "existing market-data orchestrator and readonly API healthy",
        "schema revision and ownership unchanged outside PAPER objects",
        "read-only PAPER reconciliation exact before and after forward fix",
    ),
)


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeBounds:
    max_symbols: int = 1
    max_positions: int = 1
    max_new_commands: int = 1
    max_worker_stages: int = 1
    max_runtime_seconds: int = 300
    max_candle_inputs: int = 2
    max_db_rows_touched: int = 40
    max_event_journal_growth: int = 20
    max_retry_count: int = 0
    max_resume_attempts: int = 0

    def __post_init__(self) -> None:
        values = tuple(getattr(self, name) for name in self.__slots__)
        if any(not isinstance(value, int) or value < 0 for value in values):
            raise ValueError("INVALID_RUNTIME_BOUND")
        if not 1 <= self.max_symbols <= 32 or not 1 <= self.max_worker_stages <= 5:
            raise ValueError("INVALID_RUNTIME_BOUND")


INITIAL_PRODUCTION_BOUNDS: Final = PaperProductionRuntimeBounds()


@dataclass(frozen=True, slots=True)
class ProductionPaperRuntimeTargetIdentity:
    environment_identity: str
    database_identity: str
    schema_head: str
    deployment_version: str
    change_ticket_id: str

    def __post_init__(self) -> None:
        for value in (
            self.environment_identity,
            self.database_identity,
            self.schema_head,
            self.deployment_version,
            self.change_ticket_id,
        ):
            _bounded_text(value)
        if "://" in self.database_identity:
            raise ValueError("TARGET_IDENTITY_MUST_NOT_CONTAIN_URI")


@dataclass(frozen=True, slots=True)
class ProductionPaperRuntimeEnablementArming:
    target_identity: ProductionPaperRuntimeTargetIdentity
    symbol_allowlist: tuple[str, ...]
    bounds: PaperProductionRuntimeBounds
    activated_at_utc: str
    expires_at_utc: str
    single_use: bool
    kill_switch_clear: bool

    def __post_init__(self) -> None:
        _bounded_tuple(self.symbol_allowlist, 32)
        _bounded_text(self.activated_at_utc)
        _bounded_text(self.expires_at_utc)
        if not self.single_use or not self.kill_switch_clear:
            raise ValueError("ARMING_MUST_BE_SINGLE_USE_AND_KILL_SWITCH_CLEAR")


@dataclass(frozen=True, slots=True)
class ProductionPaperRuntimeOperatorAcknowledgement:
    task_id: str
    change_ticket_id: str
    operator_identity: str
    independent_approver_identity: str
    exact_target_identity: str
    exact_deployment_version: str
    exact_schema_head: str
    exact_symbols: tuple[str, ...]
    exact_bounds: PaperProductionRuntimeBounds
    acknowledged_at_utc: str
    expires_at_utc: str

    def __post_init__(self) -> None:
        for value in (
            self.task_id,
            self.change_ticket_id,
            self.operator_identity,
            self.independent_approver_identity,
            self.exact_target_identity,
            self.exact_deployment_version,
            self.exact_schema_head,
            self.acknowledged_at_utc,
            self.expires_at_utc,
        ):
            _bounded_text(value)
        _bounded_tuple(self.exact_symbols, 32)
        if self.operator_identity == self.independent_approver_identity:
            raise ValueError("TWO_PERSON_APPROVAL_REQUIRED")


@dataclass(frozen=True, slots=True)
class PaperProductionMinimalCanaryPlan:
    symbol_count: int
    approval_count: int
    maximum_new_commands: int
    maximum_positions: int
    maximum_notional: str
    deadline_seconds: int
    observation_minutes: int
    entry_criteria: tuple[str, ...]
    success_criteria: tuple[str, ...]
    stop_criteria: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.symbol_count, self.approval_count, self.maximum_new_commands, self.maximum_positions) != (1, 1, 1, 1):
            raise ValueError("CANARY_MUST_BE_MINIMAL")
        _bounded_text(self.maximum_notional)
        _bounded_tuple(self.entry_criteria)
        _bounded_tuple(self.success_criteria)
        _bounded_tuple(self.stop_criteria)


MINIMAL_CANARY_PLAN: Final = PaperProductionMinimalCanaryPlan(
    symbol_count=1,
    approval_count=1,
    maximum_new_commands=1,
    maximum_positions=1,
    maximum_notional="change-ticket-approved hard cap",
    deadline_seconds=300,
    observation_minutes=60,
    entry_criteria=(
        "all readiness blockers closed by a separate reviewed commit",
        "backup restore and read-only reconciliation rehearsals pass",
        "exact target version schema approval and kill-switch gates pass",
    ),
    success_criteria=(
        "one ENTRY path maximum within exact mutation budget",
        "no alert security schema idempotency or cleanup failure",
        "existing services and 9 GET 0 write route policy remain healthy",
    ),
    stop_criteria=(
        "any gate mismatch unexpected mutation or observer outage",
        "market-data gap stale approval uncertain commit or lock wait",
        "operator cancellation or active global PAPER kill switch",
    ),
)


MIGRATION_PRINCIPAL_PRIVILEGES: Final = (
    "CONNECT target database",
    "USAGE and CREATE on designated schema for reviewed Alembic revisions",
    "DDL only during approved maintenance window",
    "no application runtime use",
)
RUNTIME_PRINCIPAL_PRIVILEGES: Final = (
    "CONNECT target database",
    "USAGE on designated schema",
    "SELECT INSERT UPDATE on nine PAPER tables only",
    "USAGE SELECT on PAPER-owned sequences only if introduced",
    "no CREATE ALTER DROP ownership role database grant or unrelated-table access",
)


REQUIRED_METRICS: Final = (
    "runner invocations",
    "requested and completed stages",
    "commands orders fills positions and exit decisions",
    "open closing and closed positions",
    "replay already-completed idempotency conflicts and uncertain commits",
    "postflight and mutation-budget failures",
    "cursor lag and market-data freshness",
    "fees PnL runtime duration and cleanup outcome",
)
REQUIRED_ALERTS: Final = (
    "unexpected mutation budget",
    "position stuck CLOSING or order OPEN beyond boundary",
    "cursor not advancing or market-data stale",
    "duplicate semantic identity or uncertain commit exhausted",
    "schema mismatch or unauthorized runner invocation",
    "security policy violation",
)
INCIDENT_RUNBOOKS: Final = (
    "migration failure",
    "startup denial",
    "partial durable prefix",
    "stuck OPEN or CLOSING position",
    "uncertain commit",
    "duplicate conflict",
    "market-data gap",
    "observer outage",
    "credential or secret incident",
    "host or container crash",
    "cleanup failure",
)
RELEASE_SEQUENCE: Final = (
    "freeze authoritative commit",
    "verify evidence and security",
    "capture safe production baseline",
    "verify backup and restore",
    "apply 0009 through 0012 with migration principal",
    "validate schema and existing services",
    "provision least-privilege PAPER runtime role",
    "deploy disabled PAPER artifacts",
    "run configuration-only validation",
    "run production read-only readiness dry-run",
    "arm one bounded PAPER invocation",
    "execute minimal production PAPER canary",
    "observe approved validation window",
    "expand only through separate authorization",
)
ROLLBACK_SEQUENCE: Final = (
    "activate global PAPER kill switch and deny new commands",
    "allow current child transaction to finish or fail atomically",
    "disable the PAPER application artifact without LIVE fallback",
    "capture safe state and run read-only reconciliation",
    "restore application version only when schema-compatible",
    "prefer reviewed forward fix; do not destructively downgrade PAPER data",
    "revalidate existing services schema alerts and audit preservation",
)


def blocker(code: str, severity: FindingSeverity, remediation_task: str) -> PaperProductionRuntimeReadinessBlocker:
    return PaperProductionRuntimeReadinessBlocker(
        code=code,
        severity=severity,
        description=code.replace("_", " ").lower(),
        remediation_task=remediation_task,
    )


def _finding(
    domain: PaperProductionRuntimeReadinessDomain,
    status: ReadinessStatus,
    evidence: tuple[str, ...],
    blockers: tuple[PaperProductionRuntimeReadinessBlocker, ...] = (),
    followup: str = "preserve evidence and revalidate at enablement time",
    gate: str = "exact evidence version schema and invariance match",
) -> PaperProductionRuntimeReadinessFinding:
    return PaperProductionRuntimeReadinessFinding(domain, status, evidence, blockers, followup, gate)


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeReadinessReviewRequest:
    server_branch: str
    server_head: str
    server_tree: str
    server_clean: bool
    all_evidence_hashes_match: bool
    security_evidence_hash_match: bool
    credential_revalidation_performed: bool
    protected_binding_access_count: int
    production_mutation_count: int
    production_runner_invocation_count: int
    production_paper_graph_read_count: int
    migration_rehearsal: PaperProductionMigrationRehearsalResult

    def baseline_matches(self) -> bool:
        return (
            self.server_branch == EXPECTED_SERVER_BRANCH
            and self.server_head == EXPECTED_SERVER_HEAD
            and self.server_tree == EXPECTED_SERVER_TREE
            and self.server_clean
            and self.all_evidence_hashes_match
            and self.security_evidence_hash_match
            and not self.credential_revalidation_performed
            and self.protected_binding_access_count == 0
            and self.production_mutation_count == 0
            and self.production_runner_invocation_count == 0
            and self.production_paper_graph_read_count == 0
        )


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeReadinessMatrix:
    findings: tuple[PaperProductionRuntimeReadinessFinding, ...]

    def __post_init__(self) -> None:
        domains = tuple(finding.domain for finding in self.findings)
        if len(domains) != 18 or frozenset(domains) != frozenset(PaperProductionRuntimeReadinessDomain):
            raise ValueError("EXACTLY_18_UNIQUE_DOMAINS_REQUIRED")

    @property
    def blockers(self) -> tuple[PaperProductionRuntimeReadinessBlocker, ...]:
        unique: dict[str, PaperProductionRuntimeReadinessBlocker] = {}
        for finding in self.findings:
            for item in finding.blockers:
                unique[item.code] = item
        return tuple(unique[code] for code in sorted(unique))

    def blocker_count(self, severity: FindingSeverity) -> int:
        return sum(item.severity is severity for item in self.blockers)

    @property
    def readiness(self) -> ProductionPaperRuntimeReadiness:
        if any(
            item.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)
            for item in self.blockers
        ):
            return ProductionPaperRuntimeReadiness.NOT_READY
        if any(finding.status is not ReadinessStatus.READY for finding in self.findings):
            return ProductionPaperRuntimeReadiness.NOT_READY
        return ProductionPaperRuntimeReadiness.READY


@dataclass(frozen=True, slots=True)
class PaperProductionRuntimeReadinessReviewResult:
    task_status: str
    matrix: PaperProductionRuntimeReadinessMatrix
    migration_rehearsal: PaperProductionMigrationRehearsalResult
    rollback_strategy: PaperProductionRollbackStrategy
    minimal_canary_plan: PaperProductionMinimalCanaryPlan
    recommended_next_task: str

    @property
    def readiness(self) -> ProductionPaperRuntimeReadiness:
        return self.matrix.readiness

    def render_safe_json(self) -> str:
        payload = {
            "task_id": TASK_ID,
            "task_status": self.task_status,
            "readiness": self.readiness.value,
            "domains": [
                {
                    "domain": item.domain.value,
                    "status": item.status.value,
                    "evidence": list(item.evidence),
                    "blockers": [blocker_item.code for blocker_item in item.blockers],
                    "required_followup": item.required_followup,
                    "enablement_gate": item.enablement_gate,
                }
                for item in self.matrix.findings
            ],
            "blocker_counts": {
                severity.value: self.matrix.blocker_count(severity)
                for severity in FindingSeverity
            },
            "recommended_next_task": self.recommended_next_task,
        }
        rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if len(rendered.encode("utf-8")) > MAX_SAFE_RENDER_BYTES:
            raise ValueError("SAFE_RENDER_TOO_LARGE")
        return rendered


def perform_review(request: PaperProductionRuntimeReadinessReviewRequest) -> PaperProductionRuntimeReadinessReviewResult:
    if not request.baseline_matches():
        raise ValueError("REVIEW_BASELINE_OR_GOVERNANCE_MISMATCH")

    rehearsal_ready = request.migration_rehearsal.accepted
    migration_blockers = () if rehearsal_ready else (
        blocker("ISOLATED_MIGRATION_REHEARSAL_NOT_ACCEPTED", FindingSeverity.CRITICAL, "PAPER_MIGRATION_REHEARSAL_REMEDIATION"),
    )
    findings = (
        _finding(
            PaperProductionRuntimeReadinessDomain.R1_SCHEMA_MIGRATION,
            ReadinessStatus.READY if rehearsal_ready else ReadinessStatus.NOT_READY,
            ("exact 0008 to 0012 chain statically classified", "isolated PostgreSQL 16 production-shape rehearsal required"),
            migration_blockers,
            "retain rehearsal metrics and repeat against frozen enablement commit",
            "0009 0010 0011 0012 rehearsal passes with zero destructive upgrade DDL and zero lock waits",
        ),
        _finding(
            PaperProductionRuntimeReadinessDomain.R2_ROLLBACK_FORWARD_FIX,
            ReadinessStatus.NOT_READY,
            ("0009, 0011, and 0012 downgrade drop PAPER data", "application disable plus forward fix is the safe strategy"),
            (blocker("BACKUP_RESTORE_CAPABILITY_UNPROVEN", FindingSeverity.CRITICAL, "PAPER_PRODUCTION_BACKUP_RESTORE_REHEARSAL_01"),),
            "prove backup integrity and isolated restore before enablement",
            "approved fresh backup and successful restore rehearsal with reconciliation",
        ),
        _finding(PaperProductionRuntimeReadinessDomain.R3_DEPLOYMENT_TOPOLOGY, ReadinessStatus.READY,
                 ("dedicated operator-started one-shot job selected", "no daemon scheduler auto-restart or service integration"),
                 followup="materialize disabled deployment artifact in separate task",
                 gate="one-shot no-auto-restart resource-limited identity and cleanup are manifest-enforced"),
        _finding(PaperProductionRuntimeReadinessDomain.R4_OPERATOR_AUTHORIZATION, ReadinessStatus.READY,
                 ("two-person change-ticket authorization contract specified", "single-use expiring exact acknowledgement specified"),
                 followup="bind named operators and approver through change control",
                 gate="exact target version schema symbols bounds expiry and kill-switch state match"),
        _finding(PaperProductionRuntimeReadinessDomain.R5_TARGET_ISOLATION_PERMISSIONS, ReadinessStatus.READY,
                 ("separate migration and PAPER runtime principals designed", "runtime privilege allowlist excludes ownership migration and unrelated tables"),
                 followup="provision and verify principals only in separately authorized enablement preparation",
                 gate="grant manifest plus deny probes pass and rotation revoke procedure is rehearsed"),
        _finding(PaperProductionRuntimeReadinessDomain.R6_MARKET_DATA_INPUT, ReadinessStatus.NOT_READY,
                 ("closed contiguous fresh candle contract specified", "fixtures and direct exchange fetch are not production authority"),
                 (
                     blocker("PRODUCTION_PAPER_MARKET_DATA_ADAPTER_NOT_IMPLEMENTED", FindingSeverity.CRITICAL, "PAPER_PRODUCTION_AUTHORITATIVE_INPUT_ADAPTERS_01"),
                     blocker("PRODUCTION_PAPER_APPROVAL_ADAPTER_NOT_IMPLEMENTED", FindingSeverity.CRITICAL, "PAPER_PRODUCTION_AUTHORITATIVE_INPUT_ADAPTERS_01"),
                 ),
                 "implement exact read-only market-data and final approval adapters with version freshness finality and quantity authority",
                 "closed-only contiguity freshness approval finality expiry quantity and replay tests pass"),
        _finding(PaperProductionRuntimeReadinessDomain.R7_EXECUTION_BOUNDS_STOP_CONTROLS, ReadinessStatus.NOT_READY,
                 ("initial one-symbol one-position one-command one-stage bounds specified", "bounded isolated runner does not prove continuous production runtime"),
                 (blocker("AUTHORITATIVE_GLOBAL_PAPER_KILL_SWITCH_NOT_IMPLEMENTED", FindingSeverity.CRITICAL, "PAPER_PRODUCTION_KILL_SWITCH_AND_INCIDENT_CONTROL_01"),),
                 "implement authoritative kill switch and deny-new-command control outside this review",
                 "bounds and kill switch are independently observable and fail closed"),
        _finding(PaperProductionRuntimeReadinessDomain.R8_IDEMPOTENCY_REPLAY_CONCURRENCY, ReadinessStatus.READY,
                 ("repository and child service atomicity passed isolated PostgreSQL", "single bounded runner replay resume concurrency and uncertain-commit paths passed"),
                 followup="repeat exact frozen-commit isolated acceptance before canary",
                 gate="zero duplicate material graph and exact durable-prefix recovery"),
        _finding(PaperProductionRuntimeReadinessDomain.R9_OBSERVABILITY_ALERTING, ReadinessStatus.NOT_READY,
                 ("required metric and alert matrices are specified", "production destination rotation retention and paging are not implemented"),
                 (blocker("PRODUCTION_PAPER_OBSERVABILITY_NOT_IMPLEMENTED", FindingSeverity.HIGH, "PAPER_PRODUCTION_OBSERVABILITY_AND_ALERTING_01"),),
                 "implement structured bounded correlation logs metrics alerts and incident preservation",
                 "all required signals reach an owned destination and alert drills pass"),
        _finding(PaperProductionRuntimeReadinessDomain.R10_INCIDENT_EMERGENCY_STOP, ReadinessStatus.NOT_READY,
                 ("eleven incident runbook subjects specified", "no authoritative global PAPER kill switch exists"),
                 (blocker("EMERGENCY_STOP_CONTROL_NOT_READY", FindingSeverity.CRITICAL, "PAPER_PRODUCTION_KILL_SWITCH_AND_INCIDENT_CONTROL_01"),),
                 "implement and rehearse stop semantics at every lifecycle boundary",
                 "deny new commands while active child transaction completes safely with no LIVE fallback"),
        _finding(PaperProductionRuntimeReadinessDomain.R11_DATA_RETENTION_CLEANUP, ReadinessStatus.NOT_READY,
                 ("all PAPER material and audit record classes identified", "approved retention deletion eligibility and cleanup cadence are absent"),
                 (blocker("APPROVED_PAPER_RETENTION_CONTRACT_MISSING", FindingSeverity.HIGH, "PAPER_PRODUCTION_RETENTION_AND_RECONCILIATION_01"),),
                 "approve retention legal audit deletion and bounded cleanup contract",
                 "retention ownership cadence safety constraints and evidence preservation are accepted"),
        _finding(PaperProductionRuntimeReadinessDomain.R12_BACKUP_RECOVERY_RECONCILIATION, ReadinessStatus.NOT_READY,
                 ("reconciliation invariants are specified", "no safe read-only production reconciliation command or restore proof exists"),
                 (
                     blocker("READ_ONLY_RECONCILIATION_COMMAND_NOT_IMPLEMENTED", FindingSeverity.CRITICAL, "PAPER_PRODUCTION_RETENTION_AND_RECONCILIATION_01"),
                     blocker("PITR_WAL_AVAILABILITY_UNPROVEN", FindingSeverity.HIGH, "PAPER_PRODUCTION_BACKUP_RESTORE_REHEARSAL_01"),
                 ),
                 "implement bounded read-only reconciliation and prove backup restore PITR ownership age encryption and access controls",
                 "restore rehearsal and all graph accounting ordering orphan duplicate and version checks pass"),
        _finding(PaperProductionRuntimeReadinessDomain.R13_PERFORMANCE_CAPACITY, ReadinessStatus.NOT_READY,
                 ("isolated benchmark shapes and initial SLO dimensions specified", "production-shape percentile query memory and result-size evidence pending"),
                 (blocker("PRODUCTION_SHAPE_CAPACITY_EVIDENCE_INCOMPLETE", FindingSeverity.MEDIUM, "PAPER_PRODUCTION_CAPACITY_BENCHMARK_01"),),
                 "complete repeatable isolated one-step five-step replay resume concurrency and reconciliation benchmarks",
                 "P50 P95 P99 query count transaction lock memory and log-size budgets are accepted"),
        _finding(PaperProductionRuntimeReadinessDomain.R14_API_CLIENT_EXPOSURE, ReadinessStatus.READY,
                 ("current policy is 9 GET and 0 write routes", "initial exposure is operator CLI job only with no client controls"),
                 followup="keep any write API or client control in a separate authenticated task",
                 gate="route counts remain 9 GET 0 write and client tree is unchanged"),
        _finding(PaperProductionRuntimeReadinessDomain.R15_SECURITY_SECRET_HANDLING, ReadinessStatus.READY,
                 ("immutable security remediation evidence hash matches", "credential state accepted without protected binding access or revalidation"),
                 followup="repeat permanent tracked-policy scanner and safe metadata checks at enablement time",
                 gate="no literal secret no protected access and missing protected value fails closed"),
        _finding(PaperProductionRuntimeReadinessDomain.R16_RELEASE_ROLLBACK_PROCEDURE, ReadinessStatus.READY,
                 ("fourteen-step release sequence specified", "seven-step disable plus forward-fix sequence specified"),
                 followup="turn sequence into owned change record after blockers close",
                 gate="each step has named operator evidence stop condition and no destructive default"),
        _finding(PaperProductionRuntimeReadinessDomain.R17_POST_ENABLE_VALIDATION, ReadinessStatus.READY,
                 ("minimal one-symbol one-ENTRY maximum canary plan specified", "60-minute manual observation precedes any expansion"),
                 followup="authorize observation separately; do not infer 72-hour soak",
                 gate="health locks states cursors budgets replay logs alerts and resources remain within limits"),
        _finding(PaperProductionRuntimeReadinessDomain.R18_LIVE_SEPARATION, ReadinessStatus.READY,
                 ("PAPER mode is explicit and LIVE is denied", "PAPER runner has no exchange order adapter network fetch or mode coercion"),
                 followup="preserve static dependency and configuration denial tests",
                 gate="LIVE remains out of scope not implemented and unreachable from PAPER"),
    )
    matrix = PaperProductionRuntimeReadinessMatrix(findings)
    next_task = (
        "TRADERS_ML_PAPER_TRADING_PRODUCTION_PAPER_BACKUP_RESTORE_"
        "AND_RECONCILIATION_READINESS_01"
    )
    return PaperProductionRuntimeReadinessReviewResult(
        task_status="COMPLETED",
        matrix=matrix,
        migration_rehearsal=request.migration_rehearsal,
        rollback_strategy=ROLLBACK_STRATEGY,
        minimal_canary_plan=MINIMAL_CANARY_PLAN,
        recommended_next_task=next_task,
    )


__all__ = (
    "EXPECTED_EVIDENCE_HASHES",
    "EXPECTED_SCHEMA_BASE",
    "EXPECTED_SCHEMA_HEAD",
    "FindingSeverity",
    "INITIAL_PRODUCTION_BOUNDS",
    "INCIDENT_RUNBOOKS",
    "MIGRATION_MANIFESTS",
    "MIGRATION_PRINCIPAL_PRIVILEGES",
    "MINIMAL_CANARY_PLAN",
    "PaperProductionMigrationRehearsalResult",
    "PaperProductionMinimalCanaryPlan",
    "PaperProductionRollbackStrategy",
    "PaperProductionRuntimeBounds",
    "PaperProductionRuntimeReadinessBlocker",
    "PaperProductionRuntimeReadinessDomain",
    "PaperProductionRuntimeReadinessFinding",
    "PaperProductionRuntimeReadinessMatrix",
    "PaperProductionRuntimeReadinessReviewRequest",
    "PaperProductionRuntimeReadinessReviewResult",
    "ProductionPaperRuntimeEnablementArming",
    "ProductionPaperRuntimeOperatorAcknowledgement",
    "ProductionPaperRuntimeReadiness",
    "ProductionPaperRuntimeTargetIdentity",
    "RELEASE_SEQUENCE",
    "REQUIRED_ALERTS",
    "REQUIRED_METRICS",
    "ROLLBACK_SEQUENCE",
    "ROLLBACK_STRATEGY",
    "RUNTIME_PRINCIPAL_PRIVILEGES",
    "ReadinessStatus",
    "TASK_ID",
    "perform_review",
)
