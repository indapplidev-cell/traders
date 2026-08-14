"""Fail-closed backup, restore, PITR, and recovery-readiness contracts.

The module deliberately carries no connection strings, credential material,
environment names, protected-binding locations, or executable production
operations.  Execution adapters must be task-owned and are kept outside these
policy objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Final, Mapping


EXPECTED_POSTGRESQL_MAJOR: Final = 16
EXPECTED_PAPER_SCHEMA_HEAD: Final = (
    "0015_trading_universe_activation"
)
EXPECTED_SERVER_HEAD: Final = "d605b28752fdd19e9086384c93f910fb2dc9f69d"
EXPECTED_SERVER_TREE: Final = "fd9c413ee3b083f5dd01b8d25930a1b3d58b4625"
MAX_SAFE_TEXT: Final = 256

EXPECTED_SOURCE_EVIDENCE_HASHES: Final[Mapping[str, str]] = MappingProxyType({
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
})


def _text(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_SAFE_TEXT
        or "://" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("UNSAFE_OR_INVALID_TEXT")


def _positive(value: int, code: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(code)


class PaperProductionProofState(StrEnum):
    CODE_ENFORCED = "CODE_ENFORCED"
    DOCUMENTED_REQUIRED = "DOCUMENTED_REQUIRED"
    PRODUCTION_PROVEN = "PRODUCTION_PROVEN"
    PRODUCTION_UNPROVEN = "PRODUCTION_UNPROVEN"


class PaperProductionBackupArtifactType(StrEnum):
    LOGICAL_CUSTOM = "LOGICAL_CUSTOM"
    LOGICAL_PLAIN = "LOGICAL_PLAIN"
    PHYSICAL_BASE_BACKUP = "PHYSICAL_BASE_BACKUP"


class PaperProductionBackupClass(StrEnum):
    LOGICAL = "LOGICAL"
    PHYSICAL = "PHYSICAL"


class PaperProductionIntegrityResult(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNPROVEN = "UNPROVEN"


class PaperProductionRecoveryStrategy(StrEnum):
    APPLICATION_DISABLE_PLUS_FORWARD_FIX = "APPLICATION_DISABLE_PLUS_FORWARD_FIX"
    RESTORE_APPROVED_LOGICAL_BACKUP = "RESTORE_APPROVED_LOGICAL_BACKUP"
    RESTORE_PHYSICAL_BACKUP_AND_REPLAY_WAL = "RESTORE_PHYSICAL_BACKUP_AND_REPLAY_WAL"
    NORMAL_SCHEMA_DOWNGRADE_FOR_RECOVERY_FORBIDDEN = (
        "NORMAL_SCHEMA_DOWNGRADE_FOR_RECOVERY_FORBIDDEN"
    )


class PaperProductionPitrCapability(StrEnum):
    PITR_PROVEN_ISOLATED = "PITR_PROVEN_ISOLATED"
    PITR_SUPPORTED_BUT_PRODUCTION_UNPROVEN = (
        "PITR_SUPPORTED_BUT_PRODUCTION_UNPROVEN"
    )
    PITR_PRODUCTION_METADATA_PROVEN = "PITR_PRODUCTION_METADATA_PROVEN"
    PITR_NOT_CONFIGURED = "PITR_NOT_CONFIGURED"
    PITR_UNPROVEN = "PITR_UNPROVEN"
    PITR_UNSUPPORTED_BY_CURRENT_DEPLOYMENT = (
        "PITR_UNSUPPORTED_BY_CURRENT_DEPLOYMENT"
    )


class PaperProductionPitrRecoveryTarget(StrEnum):
    TIMESTAMP = "TIMESTAMP"
    RESTORE_POINT = "RESTORE_POINT"
    TRANSACTION_ID = "TRANSACTION_ID"
    LSN = "LSN"


@dataclass(frozen=True, slots=True)
class PaperProductionBackupPolicy:
    postgresql_major: int
    logical_backup_required: bool
    physical_pitr_required: bool
    maximum_backup_age: timedelta
    retention: timedelta
    integrity_verification_required: bool
    restore_rehearsal_cadence: timedelta
    pitr_rehearsal_cadence: timedelta
    encryption_required: bool
    access_control_required: bool
    operator_owner: str
    target_rpo: timedelta
    target_rto: timedelta
    pre_migration_backup_required: bool
    policy_status: str = "PROPOSED_NOT_APPROVED"

    def __post_init__(self) -> None:
        if self.postgresql_major != EXPECTED_POSTGRESQL_MAJOR:
            raise ValueError("POSTGRESQL_MAJOR_NOT_SUPPORTED")
        for value in (
            self.maximum_backup_age,
            self.retention,
            self.restore_rehearsal_cadence,
            self.pitr_rehearsal_cadence,
            self.target_rpo,
            self.target_rto,
        ):
            if value <= timedelta(0):
                raise ValueError("NON_POSITIVE_POLICY_DURATION")
        _text(self.operator_owner)
        _text(self.policy_status)
        if not all(
            (
                self.logical_backup_required,
                self.physical_pitr_required,
                self.integrity_verification_required,
                self.encryption_required,
                self.access_control_required,
                self.pre_migration_backup_required,
            )
        ):
            raise ValueError("MANDATORY_RECOVERY_CONTROL_DISABLED")


DEFAULT_BACKUP_POLICY: Final = PaperProductionBackupPolicy(
    postgresql_major=16,
    logical_backup_required=True,
    physical_pitr_required=True,
    maximum_backup_age=timedelta(hours=24),
    retention=timedelta(days=35),
    integrity_verification_required=True,
    restore_rehearsal_cadence=timedelta(days=30),
    pitr_rehearsal_cadence=timedelta(days=90),
    encryption_required=True,
    access_control_required=True,
    operator_owner="database-operations-owner-to-be-formally-approved",
    target_rpo=timedelta(minutes=15),
    target_rto=timedelta(hours=2),
    pre_migration_backup_required=True,
)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupReadinessFinding:
    code: str
    state: PaperProductionProofState
    description: str

    def __post_init__(self) -> None:
        _text(self.code)
        _text(self.description)


@dataclass(frozen=True, slots=True)
class PaperProductionBackupReadinessResult:
    ready: bool
    findings: tuple[PaperProductionBackupReadinessFinding, ...]
    production_capability: PaperProductionProofState

    def __post_init__(self) -> None:
        if not self.findings:
            raise ValueError("READINESS_FINDINGS_REQUIRED")
        if self.ready and self.production_capability is not PaperProductionProofState.PRODUCTION_PROVEN:
            raise ValueError("PRODUCTION_READINESS_REQUIRES_PROOF")


@dataclass(frozen=True, slots=True)
class PaperProductionBackupArtifactManifest:
    artifact_type: PaperProductionBackupArtifactType
    created_at: datetime
    source_schema_head: str
    postgresql_major: int
    backup_class: PaperProductionBackupClass
    size_bytes: int
    checksum_sha256: str
    integrity_result: PaperProductionIntegrityResult
    tool_version: str
    rehearsal_id: str
    retention_class: str

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("CREATED_AT_MUST_BE_AWARE")
        _text(self.source_schema_head)
        _text(self.tool_version)
        _text(self.rehearsal_id)
        _text(self.retention_class)
        _positive(self.size_bytes, "INVALID_ARTIFACT_SIZE")
        if self.postgresql_major != EXPECTED_POSTGRESQL_MAJOR:
            raise ValueError("WRONG_POSTGRESQL_MAJOR_METADATA")
        if len(self.checksum_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.checksum_sha256
        ):
            raise ValueError("INVALID_ARTIFACT_CHECKSUM")
        expected_class = (
            PaperProductionBackupClass.PHYSICAL
            if self.artifact_type is PaperProductionBackupArtifactType.PHYSICAL_BASE_BACKUP
            else PaperProductionBackupClass.LOGICAL
        )
        if self.backup_class is not expected_class:
            raise ValueError("ARTIFACT_CLASS_MISMATCH")

    def verify_bytes(
        self,
        artifact_bytes: bytes | None,
        *,
        expected_schema_head: str = EXPECTED_PAPER_SCHEMA_HEAD,
        expected_postgresql_major: int = EXPECTED_POSTGRESQL_MAJOR,
    ) -> str:
        if artifact_bytes is None:
            return "MISSING_BACKUP"
        if self.postgresql_major != expected_postgresql_major:
            return "WRONG_POSTGRESQL_MAJOR_METADATA"
        if self.source_schema_head != expected_schema_head:
            return "WRONG_EXPECTED_SCHEMA_HEAD"
        if len(artifact_bytes) != self.size_bytes:
            return "BACKUP_SIZE_MISMATCH"
        if sha256(artifact_bytes).hexdigest() != self.checksum_sha256:
            return "BACKUP_CHECKSUM_MISMATCH"
        if self.integrity_result is not PaperProductionIntegrityResult.VERIFIED:
            return "BACKUP_INTEGRITY_NOT_VERIFIED"
        return "VERIFIED"


@dataclass(frozen=True, slots=True)
class PaperProductionRestoreRehearsalRequest:
    rehearsal_id: str
    expected_schema_head: str
    expected_postgresql_major: int
    destructive_loss_required: bool
    fresh_target_required: bool
    reconciliation_required: bool

    def __post_init__(self) -> None:
        _text(self.rehearsal_id)
        _text(self.expected_schema_head)
        if self.expected_postgresql_major != EXPECTED_POSTGRESQL_MAJOR:
            raise ValueError("WRONG_POSTGRESQL_MAJOR_METADATA")
        if not all(
            (
                self.destructive_loss_required,
                self.fresh_target_required,
                self.reconciliation_required,
            )
        ):
            raise ValueError("RESTORE_REHEARSAL_MUST_PROVE_LOSS_AND_RECOVERY")


@dataclass(frozen=True, slots=True)
class PaperProductionRestoreRehearsalResult:
    rehearsal_id: str
    passed: bool
    backup_duration_ms: int
    restore_duration_ms: int
    restored_schema_head: str
    structural_manifest_exact: bool
    material_graph_exact: bool
    reconciliation_healthy: bool
    repository_read_smoke: bool
    runtime_read_smoke: bool

    def __post_init__(self) -> None:
        _text(self.rehearsal_id)
        _text(self.restored_schema_head)
        if self.backup_duration_ms < 0 or self.restore_duration_ms < 0:
            raise ValueError("NEGATIVE_REHEARSAL_DURATION")

    @property
    def accepted(self) -> bool:
        return self.passed and self.restored_schema_head == EXPECTED_PAPER_SCHEMA_HEAD and all(
            (
                self.structural_manifest_exact,
                self.material_graph_exact,
                self.reconciliation_healthy,
                self.repository_read_smoke,
                self.runtime_read_smoke,
            )
        )


@dataclass(frozen=True, slots=True)
class PaperProductionRecoveryPoint:
    recovery_point_id: str
    created_at: datetime
    schema_head: str
    target_kind: PaperProductionPitrRecoveryTarget

    def __post_init__(self) -> None:
        _text(self.recovery_point_id)
        _text(self.schema_head)
        if self.created_at.tzinfo is None:
            raise ValueError("RECOVERY_POINT_MUST_BE_AWARE")


@dataclass(frozen=True, slots=True)
class PaperProductionPitrRehearsalRequest:
    rehearsal_id: str
    recovery_point: PaperProductionRecoveryPoint
    expected_postgresql_major: int
    require_archive_mode: bool
    require_fresh_instance: bool
    require_reconciliation: bool

    def __post_init__(self) -> None:
        _text(self.rehearsal_id)
        if self.expected_postgresql_major != EXPECTED_POSTGRESQL_MAJOR:
            raise ValueError("WRONG_POSTGRESQL_MAJOR_METADATA")
        if not all(
            (
                self.require_archive_mode,
                self.require_fresh_instance,
                self.require_reconciliation,
            )
        ):
            raise ValueError("INCOMPLETE_PITR_REHEARSAL_REQUEST")


@dataclass(frozen=True, slots=True)
class PaperProductionPitrRehearsalResult:
    rehearsal_id: str
    capability: PaperProductionPitrCapability
    target_accurate: bool
    pre_target_state_present: bool
    post_target_state_absent: bool
    schema_head_correct: bool
    reconciliation_healthy: bool
    artifacts_cleaned: bool
    reason_code: str

    def __post_init__(self) -> None:
        _text(self.rehearsal_id)
        _text(self.reason_code)

    @property
    def accepted_isolated(self) -> bool:
        return self.capability is PaperProductionPitrCapability.PITR_PROVEN_ISOLATED and all(
            (
                self.target_accurate,
                self.pre_target_state_present,
                self.post_target_state_absent,
                self.schema_head_correct,
                self.reconciliation_healthy,
                self.artifacts_cleaned,
            )
        )


@dataclass(frozen=True, slots=True)
class PaperProductionPitrReadinessResult:
    capability: PaperProductionPitrCapability
    archive_mode_enabled: bool | None
    archive_command_configured: bool | None
    backup_tooling_present: bool | None
    persistent_storage_classified: bool | None
    production_metadata_approved: bool
    reason_code: str

    def __post_init__(self) -> None:
        _text(self.reason_code)


def classify_production_pitr(
    *,
    archive_mode_enabled: bool | None,
    archive_command_configured: bool | None,
    backup_tooling_present: bool | None,
    persistent_storage_classified: bool | None,
    production_metadata_approved: bool,
) -> PaperProductionPitrReadinessResult:
    values = (
        archive_mode_enabled,
        archive_command_configured,
        backup_tooling_present,
        persistent_storage_classified,
    )
    if any(value is None for value in values) or not production_metadata_approved:
        capability = PaperProductionPitrCapability.PITR_UNPROVEN
        reason = "APPROVED_NO_ECHO_PRODUCTION_METADATA_INCOMPLETE"
    elif not archive_mode_enabled or not archive_command_configured:
        capability = PaperProductionPitrCapability.PITR_NOT_CONFIGURED
        reason = "PRODUCTION_WAL_ARCHIVING_NOT_CONFIGURED"
    elif not backup_tooling_present or not persistent_storage_classified:
        capability = PaperProductionPitrCapability.PITR_UNSUPPORTED_BY_CURRENT_DEPLOYMENT
        reason = "PRODUCTION_BACKUP_OR_PERSISTENCE_CAPABILITY_MISSING"
    else:
        capability = PaperProductionPitrCapability.PITR_PRODUCTION_METADATA_PROVEN
        reason = "APPROVED_NO_ECHO_PRODUCTION_METADATA_SUPPORTS_PITR"
    return PaperProductionPitrReadinessResult(
        capability=capability,
        archive_mode_enabled=archive_mode_enabled,
        archive_command_configured=archive_command_configured,
        backup_tooling_present=backup_tooling_present,
        persistent_storage_classified=persistent_storage_classified,
        production_metadata_approved=production_metadata_approved,
        reason_code=reason,
    )


DESTRUCTIVE_DOWNGRADE_RECOVERY_STEPS: Final = (
    "disable PAPER and deny new work",
    "preserve the database and capture approved safe metadata",
    "select an approved backup restore or a tested forward fix",
    "validate exact schema and run read-only reconciliation",
    "resume only after explicit operator authorization",
)


RECOVERY_INCIDENT_CLASSES: Final = (
    "MIGRATION_FAILURE_BEFORE_PAPER_DATA",
    "PARTIAL_MIGRATION_FAILURE",
    "RUNTIME_DEPLOYMENT_FAILURE",
    "PAPER_CORRUPTION_SUSPICION",
    "RUNNER_CRASH_AFTER_DURABLE_PREFIX",
    "DATABASE_LOSS",
    "CONTAINER_OR_HOST_LOSS",
    "BACKUP_CORRUPTION",
    "PITR_FAILURE",
    "RECONCILIATION_FAILURE_AFTER_RESTORE",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [name for name in globals() if name.startswith("PaperProduction")]
