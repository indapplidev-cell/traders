"""Immutable, secret-free production backup/PITR infrastructure contracts.

These objects describe preflight, publication, restore, governance and
readiness.  They deliberately cannot execute a production backup, restore,
PITR, migration, role change, restart, or protected-binding read.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Mapping

from app.engine_paper.recovery_readiness import (
    EXPECTED_PAPER_SCHEMA_HEAD,
    EXPECTED_POSTGRESQL_MAJOR,
)


MAX_SAFE_TEXT: Final = 160
PROPOSED_RPO: Final = timedelta(minutes=15)
PROPOSED_RTO: Final = timedelta(hours=2)
PROPOSED_MAX_BACKUP_AGE: Final = timedelta(hours=24)
PROPOSED_RESTORE_REHEARSAL_CADENCE: Final = timedelta(days=30)
PROPOSED_PITR_REHEARSAL_CADENCE: Final = timedelta(days=90)
EXPECTED_SERVER_HEAD: Final = "8261813645e1f2c4a603ac8a58bfabfb0d4f926b"
EXPECTED_SERVER_TREE: Final = "29fb3865378d055fcb010f3cb86d25ff4b2ef1f4"
EXPECTED_EVIDENCE_HASHES: Final[Mapping[str, str]] = MappingProxyType({
    "FOUNDATION": "0b430bcc838eeffa7f6044425884ea1420ea3497bb8ecc994ba4e6be9dc5a8bb",
    "DOMAIN": "cdb435175ef28d5a3f83dd80f8b25a2e8fdc53c482148e1024a2ae23f50e0b1b",
    "PERSISTENCE": "823536365958424349da8085660093c285e1dcd94471f10358d18f43f4af22ef",
    "REPOSITORY": "e4230d9d15bb3f62a49a7195d3a92f03b07fe7d44a0370f78f2b7f9573793e9d",
    "FILL_SIMULATOR": "db00f888b92e142eae30d1a8163ee0169deef3546fb6d456f50d6eb998c78328",
    "ORDER_EXECUTION": "57848a81be3c18eadd86e95e438b3bc4ede3869d3db9b0908ba9f7a460e81339",
    "FINAL_APPROVAL": "91d4bcff673ca53a2b21de81a507fb4befcac5587aeca775bdffeae5f117187d",
    "COMMAND_INGESTION": "f217e8b7b5c8821be1130da7b923784b938f4abc4f623b7e621e5716ad1f614e",
    "CLOSE_CAUSAL_CURSOR": "f3e43ce5c57691771624be5e61f11c41476c1e15d932f21a2c83a8db5c9af3c1",
    "EXIT_EVALUATION": "5b33f878d60dd564e143463bdadcf8f5ff3e6b5b541cb3006075574ba42e849a",
    "ENTRY_CURSOR": "bde21a3794bf5dc008a0c041f201c0b433fd52fea3d4f352a363d72a4ec14f16",
    "CONTROLLED_WORKER": "1434340044d248d1832ca3752a235d3de7113f3cf02c282c1936034cdad8c037",
    "CONTROLLED_RUNTIME": "287b46c1018aac8315817d1ac876a894bbe4fa695fd64bc7f5e729c16f91db73",
    "FAILED_CANARY": "dbd41caa1a338ef9689453e75cb8bf07c53ecc8942bc41d3349687bb1ba99c23",
    "BLOCKED_SECURITY": "be9897866fb26bee73f5db5b84caea2011ddaeeaa812f68ad62c5a0a44454753",
    "SECURITY_PASS": "afce8eae9d58135a3d9d1e5591cbb0ede5546a90030a9885fb9427d4e6edeaa0",
    "BLOCKED_CANARY_RETRY_01": "64496b15a3dc33157ae4a1bd230154368d0254c5ce164abff061974516c59900",
    "SINGLE_CYCLE_CANARY": "c9ef780f6c16e1a06564d4b879c416df609821dae9ccf141949bceefa44b22b4",
    "BOUNDED_SEQUENCE_CANARY": "d97cab0ec98de5cbab640da5548789efbd5a3bc4f8335cc2b51e4f9ed1618776",
    "OPERATOR_RUNNER": "18e7b78381c0bc0de043c96c870c35ebbcb7cfb665f233bd1d5a23d6fee517db",
    "PRODUCTION_READINESS_REVIEW": "7754627e41a7e78078674602caad8cf66231297008727c1b4deb5718b206e1ad",
    "BACKUP_RESTORE_RECONCILIATION_READINESS": "0c3ec914a435bf5f6da8d616e2375190bcec80066e6e63c9b1b4474bf67734ec",
})


def _safe(value: str) -> None:
    forbidden = ("://", "password", "secret", "token", "database_url", "\\", "/")
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_SAFE_TEXT
        or any(ord(character) < 32 for character in value)
        or any(item in value.casefold() for item in forbidden)
    ):
        raise ValueError("UNSAFE_TEXT")


class Readiness(StrEnum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    UNPROVEN = "UNPROVEN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class StorageClass(StrEnum):
    FILESYSTEM = "FILESYSTEM"
    OBJECT_STORAGE = "OBJECT_STORAGE"
    MANAGED_BACKUP = "MANAGED_BACKUP"
    UNPROVEN = "UNPROVEN"


class PersistenceClass(StrEnum):
    PERSISTENT_EXTERNAL_VOLUME = "PERSISTENT_EXTERNAL_VOLUME"
    PERSISTENT_HOST_BIND = "PERSISTENT_HOST_BIND"
    MANAGED_PERSISTENT_STORAGE = "MANAGED_PERSISTENT_STORAGE"
    EPHEMERAL_CONTAINER_STORAGE = "EPHEMERAL_CONTAINER_STORAGE"
    UNPROVEN = "UNPROVEN"


class AccessControlClass(StrEnum):
    LEAST_PRIVILEGE_SEPARATE_BACKUP_ROLE = "LEAST_PRIVILEGE_SEPARATE_BACKUP_ROLE"
    MANAGED_SERVICE_POLICY = "MANAGED_SERVICE_POLICY"
    PROPOSED_NOT_APPROVED = "PROPOSED_NOT_APPROVED"
    UNPROVEN = "UNPROVEN"


class RetentionClass(StrEnum):
    APPROVED_BOUNDED = "APPROVED_BOUNDED"
    PROPOSED_BOUNDED = "PROPOSED_BOUNDED"
    UNBOUNDED = "UNBOUNDED"
    UNPROVEN = "UNPROVEN"


class PublicationState(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    CHECKSUM_VERIFIED = "CHECKSUM_VERIFIED"
    MANIFEST_VERIFIED = "MANIFEST_VERIFIED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class MutationClass(StrEnum):
    NO_RESTART_SAFE_METADATA_CHANGE = "NO_RESTART_SAFE_METADATA_CHANGE"
    TARGETED_RELOAD_REQUIRED = "TARGETED_RELOAD_REQUIRED"
    POSTGRES_RESTART_REQUIRED = "POSTGRES_RESTART_REQUIRED"
    CONTAINER_RECREATE_REQUIRED = "CONTAINER_RECREATE_REQUIRED"
    HOST_CONFIGURATION_REQUIRED = "HOST_CONFIGURATION_REQUIRED"
    EXTERNAL_STORAGE_REQUIRED = "EXTERNAL_STORAGE_REQUIRED"


class RecoveryDecision(StrEnum):
    FORWARD_FIX = "DISABLE_PAPER_FORWARD_FIX_RECONCILE"
    RESTORE = "ISOLATED_VALIDATE_APPROVED_RESTORE_RECONCILE"
    PITR = "APPROVED_PITR_TARGET_RECONCILE"
    HARD_INCIDENT = "HARD_INCIDENT_NO_RESUME"


@dataclass(frozen=True, slots=True)
class PaperProductionBackupStoragePolicy:
    storage_class: StorageClass
    persistence_class: PersistenceClass
    encryption_at_rest_required: bool
    access_control_class: AccessControlClass
    retention_class: RetentionClass
    capacity_floor_bytes: int
    minimum_free_space_bytes: int
    atomic_publish_required: bool
    partial_artifact_quarantine_or_removal: bool
    manifest_checksum_required: bool
    owner_role_class: str

    def __post_init__(self) -> None:
        _safe(self.owner_role_class)
        if self.capacity_floor_bytes <= 0 or self.minimum_free_space_bytes <= 0:
            raise ValueError("CAPACITY_FLOOR_REQUIRED")
        if self.minimum_free_space_bytes < self.capacity_floor_bytes:
            raise ValueError("MINIMUM_FREE_SPACE_BELOW_FLOOR")
        if not all((self.encryption_at_rest_required, self.atomic_publish_required,
                    self.partial_artifact_quarantine_or_removal, self.manifest_checksum_required)):
            raise ValueError("MANDATORY_STORAGE_CONTROL_DISABLED")


@dataclass(frozen=True, slots=True)
class PaperProductionBackupDestinationIdentity:
    opaque_identity: str
    storage_class: StorageClass
    persistence_class: PersistenceClass
    outside_postgres_data_directory: bool
    outside_ephemeral_container_layer: bool
    outside_git_repository: bool
    outside_project_temp: bool
    retention_bounded: bool
    approved_for_backup_restore: bool

    def __post_init__(self) -> None:
        _safe(self.opaque_identity)

    @property
    def valid(self) -> bool:
        return self.persistence_class in {
            PersistenceClass.PERSISTENT_EXTERNAL_VOLUME,
            PersistenceClass.PERSISTENT_HOST_BIND,
            PersistenceClass.MANAGED_PERSISTENT_STORAGE,
        } and all((self.outside_postgres_data_directory,
                   self.outside_ephemeral_container_layer,
                   self.outside_git_repository, self.outside_project_temp,
                   self.retention_bounded, self.approved_for_backup_restore))


@dataclass(frozen=True, slots=True)
class PaperProductionBackupStorageReadinessResult:
    readiness: Readiness
    destination_valid: bool
    capacity_ready: bool
    access_control_ready: bool
    retention_ready: bool
    reason_code: str

    def __post_init__(self) -> None:
        _safe(self.reason_code)
        proofs = all((self.destination_valid, self.capacity_ready,
                      self.access_control_ready, self.retention_ready))
        if self.readiness is Readiness.READY and not proofs:
            raise ValueError("STORAGE_READY_WITHOUT_ALL_PROOFS")


@dataclass(frozen=True, slots=True)
class PaperProductionBackupIntegrityPolicy:
    sha256_required: bool = True
    tool_integrity_check_required: bool = True
    manifest_schema_check_required: bool = True
    size_check_required: bool = True
    verify_before_publish: bool = True
    failed_artifact_never_valid: bool = True

    def __post_init__(self) -> None:
        if not all(getattr(self, field.name) for field in fields(self)):
            raise ValueError("INTEGRITY_CONTROL_DISABLED")


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPublicationResult:
    state: PublicationState
    tool_completed: bool
    checksum_verified: bool
    manifest_verified: bool
    atomic_publish_completed: bool
    partial_artifact_published: bool
    failure_code: str = "NONE"

    def __post_init__(self) -> None:
        _safe(self.failure_code)
        complete = all((self.tool_completed, self.checksum_verified,
                        self.manifest_verified, self.atomic_publish_completed))
        if self.state is PublicationState.PUBLISHED and (not complete or self.partial_artifact_published):
            raise ValueError("INVALID_PUBLICATION")
        if self.state is not PublicationState.PUBLISHED and self.atomic_publish_completed:
            raise ValueError("UNPUBLISHED_CANNOT_BE_ATOMICALLY_PUBLISHED")

    @classmethod
    def evaluate(cls, *, tool_completed: bool, checksum_verified: bool,
                 manifest_verified: bool, capacity_ready: bool,
                 atomic_rename_completed: bool) -> "PaperProductionBackupPublicationResult":
        ordered = (tool_completed, checksum_verified, manifest_verified,
                   capacity_ready, atomic_rename_completed)
        if all(ordered):
            return cls(PublicationState.PUBLISHED, True, True, True, True, False)
        failure = (
            "TOOL_FAILURE" if not tool_completed else
            "CHECKSUM_MISMATCH" if not checksum_verified else
            "MANIFEST_MISMATCH" if not manifest_verified else
            "DESTINATION_CAPACITY_FAILURE" if not capacity_ready else
            "ATOMIC_PUBLISH_FAILURE"
        )
        return cls(PublicationState.FAILED, tool_completed, checksum_verified,
                   manifest_verified, False, False, failure)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupCommandContract:
    approved_source_identity: bool
    approved_persistent_destination: bool
    password_absent_from_argv: bool
    uri_absent_from_argv: bool
    environment_dump_forbidden: bool
    checksum_after_success: bool
    manifest_verification: bool
    atomic_publish_after_verification_only: bool
    failed_partial_never_valid: bool
    bounded_logs: bool

    @property
    def ready(self) -> bool:
        return all(getattr(self, field.name) for field in fields(self))


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPreflight:
    environment_identity: str
    postgresql_major: int
    schema_head: str
    destination_approved: bool
    destination_persistent: bool
    capacity_sufficient: bool
    tooling_present: bool
    policy_approved: bool
    operator_authorized: bool
    valid_backup_age_known: bool
    pitr_state_known: bool
    protected_binding_access_count: int

    def __post_init__(self) -> None:
        _safe(self.environment_identity)
        _safe(self.schema_head)
        if self.protected_binding_access_count != 0:
            raise ValueError("PROTECTED_BINDING_ACCESS_FORBIDDEN")

    def evaluate(self) -> "PaperProductionBackupPreflightResult":
        checks = {
            "environment": self.environment_identity == "PRODUCTION",
            "postgres_major": self.postgresql_major == EXPECTED_POSTGRESQL_MAJOR,
            "schema": self.schema_head in {"0008_engine_orchestrator_freshness_retry", EXPECTED_PAPER_SCHEMA_HEAD},
            "destination": self.destination_approved and self.destination_persistent,
            "capacity": self.capacity_sufficient,
            "tooling": self.tooling_present,
            "policy": self.policy_approved,
            "operator": self.operator_authorized,
            "backup_age": self.valid_backup_age_known,
            "pitr": self.pitr_state_known,
            "zero_binding": self.protected_binding_access_count == 0,
        }
        failed = tuple(name for name, passed in checks.items() if not passed)
        return PaperProductionBackupPreflightResult(not failed, failed, len(checks))


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPreflightResult:
    passed: bool
    failed_checks: tuple[str, ...]
    checks_run: int

    def __post_init__(self) -> None:
        if self.checks_run != 11 or self.passed == bool(self.failed_checks):
            raise ValueError("INCONSISTENT_BACKUP_PREFLIGHT_RESULT")


@dataclass(frozen=True, slots=True)
class PaperProductionRestoreProcedure:
    select_approved_artifact: bool = True
    verify_checksum_manifest: bool = True
    verify_postgresql_compatibility: bool = True
    restore_isolated_first: bool = True
    verify_alembic_head: bool = True
    run_reconciliation: bool = True
    repository_read_smoke: bool = True
    explicit_production_recovery_approval: bool = True

    @property
    def complete(self) -> bool:
        return all(getattr(self, field.name) for field in fields(self))


@dataclass(frozen=True, slots=True)
class PaperProductionRestorePreflight:
    artifact_exists: bool
    checksum_manifest_valid: bool
    engine_compatible: bool
    schema_metadata_valid: bool
    isolated_target: bool
    capacity_sufficient: bool
    reconciliation_available: bool
    operator_authorized: bool
    production_target_requested: bool

    def evaluate(self) -> "PaperProductionRestorePreflightResult":
        checks = (
            self.artifact_exists, self.checksum_manifest_valid,
            self.engine_compatible, self.schema_metadata_valid,
            self.isolated_target, self.capacity_sufficient,
            self.reconciliation_available, self.operator_authorized,
            not self.production_target_requested,
        )
        return PaperProductionRestorePreflightResult(
            passed=all(checks), production_target_rejected=self.production_target_requested,
            failed_check_count=sum(not item for item in checks),
        )


@dataclass(frozen=True, slots=True)
class PaperProductionRestorePreflightResult:
    passed: bool
    production_target_rejected: bool
    failed_check_count: int

    def __post_init__(self) -> None:
        if self.failed_check_count < 0 or self.passed == (self.failed_check_count > 0):
            raise ValueError("INCONSISTENT_RESTORE_PREFLIGHT_RESULT")


@dataclass(frozen=True, slots=True)
class PaperProductionRestorePostflight:
    schema_head_correct: bool
    reconciliation_healthy: bool
    repository_read_smoke: bool
    explicit_resume_authorization: bool

    @property
    def passed(self) -> bool:
        return all(getattr(self, field.name) for field in fields(self))


@dataclass(frozen=True, slots=True)
class PaperProductionRetentionPolicy:
    minimum_retained_full_backups: int
    minimum_pitr_window: timedelta
    maximum_artifact_age: timedelta
    cleanup_safety_floor: int
    never_delete_last_known_good: bool
    never_delete_base_required_by_wal: bool
    bounded_deletion_batch: int
    dry_run_before_cleanup: bool
    approved: bool

    def __post_init__(self) -> None:
        if min(self.minimum_retained_full_backups, self.cleanup_safety_floor,
               self.bounded_deletion_batch) <= 0:
            raise ValueError("INVALID_RETENTION_FLOOR")
        if self.minimum_pitr_window <= timedelta(0) or self.maximum_artifact_age <= timedelta(0):
            raise ValueError("INVALID_RETENTION_DURATION")
        if not all((self.never_delete_last_known_good,
                    self.never_delete_base_required_by_wal,
                    self.dry_run_before_cleanup)):
            raise ValueError("UNSAFE_RETENTION_POLICY")


@dataclass(frozen=True, slots=True)
class PaperProductionCapacityAssessment:
    expected_full_backup_bytes: int | None
    pitr_retention_reserve_bytes: int | None
    available_bytes: int | None

    @property
    def required_free_space_bytes(self) -> int | None:
        if self.expected_full_backup_bytes is None or self.pitr_retention_reserve_bytes is None:
            return None
        return max(2 * self.expected_full_backup_bytes,
                   self.expected_full_backup_bytes + self.pitr_retention_reserve_bytes)

    @property
    def readiness(self) -> Readiness:
        required = self.required_free_space_bytes
        if required is None or self.available_bytes is None:
            return Readiness.UNPROVEN
        return Readiness.READY if self.available_bytes >= required else Readiness.NOT_READY


@dataclass(frozen=True, slots=True)
class PaperProductionRecoveryObjectivePolicy:
    target_rpo: timedelta = PROPOSED_RPO
    target_rto: timedelta = PROPOSED_RTO
    maximum_backup_age: timedelta = PROPOSED_MAX_BACKUP_AGE
    restore_rehearsal_cadence: timedelta = PROPOSED_RESTORE_REHEARSAL_CADENCE
    pitr_rehearsal_cadence: timedelta = PROPOSED_PITR_REHEARSAL_CADENCE
    status: str = "PROPOSED_NOT_APPROVED"

    def __post_init__(self) -> None:
        _safe(self.status)
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, timedelta) and value <= timedelta(0):
                raise ValueError("INVALID_RECOVERY_OBJECTIVE")


@dataclass(frozen=True, slots=True)
class PaperProductionRecoveryObjectiveApproval:
    policy: PaperProductionRecoveryObjectivePolicy
    approval_evidence_present: bool
    approval_authority_class: str

    def __post_init__(self) -> None:
        _safe(self.approval_authority_class)

    @property
    def approved(self) -> bool:
        return self.approval_evidence_present and self.policy.status == "APPROVED"


@dataclass(frozen=True, slots=True)
class PaperProductionOperatorRole:
    role_class: str
    allowed_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    change_ticket_required: bool
    evidence_required: bool
    two_person_gate: bool

    def __post_init__(self) -> None:
        _safe(self.role_class)
        for value in (*self.allowed_actions, *self.forbidden_actions):
            _safe(value)
        if not self.allowed_actions or not self.forbidden_actions:
            raise ValueError("OPERATOR_ACTION_BOUNDARIES_REQUIRED")


@dataclass(frozen=True, slots=True)
class PaperProductionOperatorOwnership:
    roles: tuple[PaperProductionOperatorRole, ...]
    approved: bool

    @property
    def complete(self) -> bool:
        expected = {"backup-operator", "restore-operator", "pitr-operator",
                    "incident-commander", "paper-runtime-operator", "approval-authority"}
        return {role.role_class for role in self.roles} == expected


MONITORING_METRICS: Final = (
    "last-successful-backup-age", "backup-size", "backup-duration",
    "verification-status", "destination-free-space", "failed-backup-count",
    "wal-archive-lag", "wal-archive-failures", "oldest-recovery-point",
    "base-backup-age", "restore-rehearsal-age", "pitr-rehearsal-age",
)
MONITORING_ALERTS: Final = (
    "backup-too-old", "verification-failed", "no-valid-backup", "low-capacity",
    "wal-archive-stalled", "wal-retention-gap", "restore-rehearsal-overdue",
    "pitr-rehearsal-overdue",
)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupMonitoringPolicy:
    metrics: tuple[str, ...]
    alerts: tuple[str, ...]
    implemented_or_accepted: bool

    @property
    def complete(self) -> bool:
        return set(self.metrics) == set(MONITORING_METRICS) and set(self.alerts) == set(MONITORING_ALERTS)


@dataclass(frozen=True, slots=True)
class PaperProductionPitrRemediationPlan:
    archive_mode_on: bool
    appropriate_wal_level: bool
    persistent_wal_archive: bool
    safe_archive_mechanism: bool
    base_backup_cadence: bool
    wal_retention_covers_window: bool
    archive_health_monitoring: bool
    restore_command_contract: bool
    recovery_target_support: bool
    timeline_policy: bool
    isolated_restore_environment: bool
    mutation_classes: tuple[MutationClass, ...]
    applied: bool = False

    @property
    def complete_specification(self) -> bool:
        controls = tuple(getattr(self, field.name) for field in fields(self)[:11])
        return all(controls) and bool(self.mutation_classes)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPitrInfrastructureFinding:
    code: str
    domain: str
    readiness: Readiness
    severity: Severity
    evidence: str
    blocker: str
    remediation: str
    closure_condition: str

    def __post_init__(self) -> None:
        for value in (self.code, self.domain, self.evidence, self.blocker,
                      self.remediation, self.closure_condition):
            _safe(value)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPitrInfrastructureDomain:
    domain_id: str
    name: str
    readiness: Readiness
    findings: tuple[PaperProductionBackupPitrInfrastructureFinding, ...]

    def __post_init__(self) -> None:
        _safe(self.domain_id)
        _safe(self.name)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPitrInfrastructureReadinessRequest:
    request_id: str
    expected_server_head: str
    expected_server_tree: str
    production_mutations_allowed: bool = False
    protected_binding_access_allowed: bool = False

    def __post_init__(self) -> None:
        for value in (self.request_id, self.expected_server_head, self.expected_server_tree):
            _safe(value)
        if self.production_mutations_allowed or self.protected_binding_access_allowed:
            raise ValueError("TASK_SCOPE_FORBIDS_PRODUCTION_OR_BINDING_MUTATION")


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPitrInfrastructureRemediationPlan:
    required_changes: tuple[str, ...]
    mutation_classes: tuple[MutationClass, ...]
    recommended_next_task: str

    def __post_init__(self) -> None:
        _safe(self.recommended_next_task)
        for change in self.required_changes:
            _safe(change)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPitrInfrastructureReadinessResult:
    overall_readiness: Readiness
    domains: tuple[PaperProductionBackupPitrInfrastructureDomain, ...]
    backup_mechanism: Readiness
    storage: Readiness
    restore_applicability: Readiness
    pitr_config: Readiness
    archive_persistence: Readiness
    rpo_rto_approval: Readiness
    operator_ownership: Readiness
    capacity: Readiness
    monitoring: Readiness
    critical_blockers: int
    high_blockers: int
    blocker_closed: bool
    remediation_plan: PaperProductionBackupPitrInfrastructureRemediationPlan

    def __post_init__(self) -> None:
        if len(self.domains) != 15 or self.critical_blockers < 0 or self.high_blockers < 0:
            raise ValueError("INCOMPLETE_READINESS_RESULT")
        required = (self.backup_mechanism, self.storage, self.restore_applicability,
                    self.pitr_config, self.archive_persistence, self.rpo_rto_approval,
                    self.operator_ownership, self.capacity, self.monitoring)
        if self.blocker_closed and (any(item is not Readiness.READY for item in required)
                                    or self.critical_blockers or self.high_blockers):
            raise ValueError("BLOCKER_CLOSED_WITHOUT_ALL_PROOFS")


def storage_readiness(
    destination: PaperProductionBackupDestinationIdentity,
    *, capacity_ready: bool, access_control_ready: bool, retention_ready: bool,
) -> PaperProductionBackupStorageReadinessResult:
    proofs = (destination.valid, capacity_ready, access_control_ready, retention_ready)
    return PaperProductionBackupStorageReadinessResult(
        Readiness.READY if all(proofs) else Readiness.NOT_READY,
        destination.valid, capacity_ready, access_control_ready, retention_ready,
        "STORAGE_READY" if all(proofs) else "APPROVED_PERSISTENT_DESTINATION_MISSING",
    )


def recovery_decision(*, database_intact: bool, data_corrupted_or_lost: bool,
                      valid_backup: bool, pitr_available: bool) -> RecoveryDecision:
    if database_intact and not data_corrupted_or_lost:
        return RecoveryDecision.FORWARD_FIX
    if data_corrupted_or_lost and valid_backup:
        return RecoveryDecision.RESTORE
    if data_corrupted_or_lost and pitr_available:
        return RecoveryDecision.PITR
    return RecoveryDecision.HARD_INCIDENT


PROPOSED_RECOVERY_OBJECTIVES: Final = PaperProductionRecoveryObjectivePolicy()
DEFAULT_INTEGRITY_POLICY: Final = PaperProductionBackupIntegrityPolicy()


def proposed_operator_ownership() -> PaperProductionOperatorOwnership:
    roles = tuple(
        PaperProductionOperatorRole(
            role, ("perform-approved-scoped-action",),
            ("unapproved-production-mutation",), True, True,
            role in {"restore-operator", "pitr-operator", "approval-authority"},
        )
        for role in (
            "backup-operator", "restore-operator", "pitr-operator",
            "incident-commander", "paper-runtime-operator", "approval-authority",
        )
    )
    return PaperProductionOperatorOwnership(roles, approved=False)


PROPOSED_OPERATOR_OWNERSHIP: Final = proposed_operator_ownership()
PROPOSED_MONITORING_POLICY: Final = PaperProductionBackupMonitoringPolicy(
    MONITORING_METRICS, MONITORING_ALERTS, implemented_or_accepted=False
)


__all__ = [name for name in globals() if name.startswith("PaperProduction")]
