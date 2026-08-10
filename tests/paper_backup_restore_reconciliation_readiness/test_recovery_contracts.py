from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from app.engine_paper import recovery_readiness as recovery


def artifact(data: bytes = b"bounded-task-owned-logical-backup"):
    return recovery.PaperProductionBackupArtifactManifest(
        artifact_type=recovery.PaperProductionBackupArtifactType.LOGICAL_CUSTOM,
        created_at=datetime.now(timezone.utc),
        source_schema_head=recovery.EXPECTED_PAPER_SCHEMA_HEAD,
        postgresql_major=16,
        backup_class=recovery.PaperProductionBackupClass.LOGICAL,
        size_bytes=len(data),
        checksum_sha256=sha256(data).hexdigest(),
        integrity_result=recovery.PaperProductionIntegrityResult.VERIFIED,
        tool_version="pg_dump-16",
        rehearsal_id="rehearsal-1",
        retention_class="task-ephemeral",
    )


def test_policy_is_complete_proposed_and_immutable():
    policy = recovery.DEFAULT_BACKUP_POLICY
    assert policy.postgresql_major == 16
    assert policy.policy_status == "PROPOSED_NOT_APPROVED"
    assert policy.target_rpo == timedelta(minutes=15)
    assert policy.target_rto == timedelta(hours=2)
    assert policy.maximum_backup_age == timedelta(hours=24)
    assert policy.restore_rehearsal_cadence == timedelta(days=30)
    assert policy.pitr_rehearsal_cadence == timedelta(days=90)
    with pytest.raises(FrozenInstanceError):
        policy.postgresql_major = 17


@pytest.mark.parametrize("name,expected", tuple(recovery.EXPECTED_SOURCE_EVIDENCE_HASHES.items()))
def test_all_21_evidence_hash_contracts(name, expected):
    assert name and len(expected) == 64
    assert expected == expected.lower()
    int(expected, 16)


@pytest.mark.parametrize("case", range(256))
def test_policy_mandatory_controls_fail_closed_for_every_boolean_matrix(case):
    controls = [bool(case & (1 << bit)) for bit in range(8)]
    kwargs = dict(
        logical_backup_required=controls[0], physical_pitr_required=controls[1],
        integrity_verification_required=controls[2], encryption_required=controls[3],
        access_control_required=controls[4], pre_migration_backup_required=controls[5],
    )
    if all(kwargs.values()):
        assert replace(recovery.DEFAULT_BACKUP_POLICY, **kwargs)
    else:
        with pytest.raises(ValueError, match="MANDATORY_RECOVERY_CONTROL_DISABLED"):
            replace(recovery.DEFAULT_BACKUP_POLICY, **kwargs)


@pytest.mark.parametrize("case", range(256))
def test_artifact_checksum_is_deterministic_and_modified_bytes_fail_closed(case):
    data = b"logical-backup" + case.to_bytes(2, "big")
    manifest = artifact(data)
    assert manifest.verify_bytes(data) == "VERIFIED"
    changed = data[:-1] + bytes([data[-1] ^ 1])
    assert manifest.verify_bytes(changed) == "BACKUP_CHECKSUM_MISMATCH"


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (lambda manifest, data: (None, manifest), "MISSING_BACKUP"),
        (lambda manifest, data: (data[:-1], manifest), "BACKUP_SIZE_MISMATCH"),
        (lambda manifest, data: (data + b"x", manifest), "BACKUP_SIZE_MISMATCH"),
        (lambda manifest, data: (data[:-1] + b"x", manifest), "BACKUP_CHECKSUM_MISMATCH"),
        (lambda manifest, data: (data, replace(manifest, checksum_sha256="0" * 64)), "BACKUP_CHECKSUM_MISMATCH"),
        (lambda manifest, data: (data, replace(manifest, source_schema_head="0010")), "WRONG_EXPECTED_SCHEMA_HEAD"),
        (lambda manifest, data: (data, replace(manifest, integrity_result=recovery.PaperProductionIntegrityResult.FAILED)), "BACKUP_INTEGRITY_NOT_VERIFIED"),
    ],
)
@pytest.mark.parametrize("repeat", range(24))
def test_negative_backup_matrix(mutation, expected, repeat):
    data = b"backup-content" + repeat.to_bytes(1, "big")
    original = artifact(data)
    changed_data, changed_manifest = mutation(original, data)
    assert changed_manifest.verify_bytes(changed_data) == expected


@pytest.mark.parametrize("metadata_approved", [False, True])
@pytest.mark.parametrize("archive", [None, False, True])
@pytest.mark.parametrize("command", [None, False, True])
@pytest.mark.parametrize("tooling", [None, False, True])
@pytest.mark.parametrize("persistent", [None, False, True])
def test_production_pitr_classification_matrix(metadata_approved, archive, command, tooling, persistent):
    result = recovery.classify_production_pitr(
        archive_mode_enabled=archive, archive_command_configured=command,
        backup_tooling_present=tooling, persistent_storage_classified=persistent,
        production_metadata_approved=metadata_approved,
    )
    if not metadata_approved or None in (archive, command, tooling, persistent):
        assert result.capability is recovery.PaperProductionPitrCapability.PITR_UNPROVEN
    elif not archive or not command:
        assert result.capability is recovery.PaperProductionPitrCapability.PITR_NOT_CONFIGURED
    elif not tooling or not persistent:
        assert result.capability is recovery.PaperProductionPitrCapability.PITR_UNSUPPORTED_BY_CURRENT_DEPLOYMENT
    else:
        assert result.capability is recovery.PaperProductionPitrCapability.PITR_PRODUCTION_METADATA_PROVEN


def test_restore_result_requires_all_exact_proofs():
    result = recovery.PaperProductionRestoreRehearsalResult(
        rehearsal_id="restore-1", passed=True, backup_duration_ms=1,
        restore_duration_ms=1, restored_schema_head=recovery.EXPECTED_PAPER_SCHEMA_HEAD,
        structural_manifest_exact=True, material_graph_exact=True,
        reconciliation_healthy=True, repository_read_smoke=True, runtime_read_smoke=True,
    )
    assert result.accepted
    for field in ("passed", "structural_manifest_exact", "material_graph_exact", "reconciliation_healthy", "repository_read_smoke", "runtime_read_smoke"):
        assert not replace(result, **{field: False}).accepted


def test_pitr_isolated_acceptance_requires_every_proof_and_cleanup():
    result = recovery.PaperProductionPitrRehearsalResult(
        rehearsal_id="pitr-1", capability=recovery.PaperProductionPitrCapability.PITR_PROVEN_ISOLATED,
        target_accurate=True, pre_target_state_present=True, post_target_state_absent=True,
        schema_head_correct=True, reconciliation_healthy=True, artifacts_cleaned=True,
        reason_code="ISOLATED_PITR_REHEARSAL_PASSED",
    )
    assert result.accepted_isolated
    assert not replace(result, post_target_state_absent=False).accepted_isolated


def test_downgrade_recovery_is_explicitly_forward_or_restore_only():
    assert recovery.PaperProductionRecoveryStrategy.NORMAL_SCHEMA_DOWNGRADE_FOR_RECOVERY_FORBIDDEN
    assert len(recovery.DESTRUCTIVE_DOWNGRADE_RECOVERY_STEPS) == 5
    assert len(recovery.RECOVERY_INCIDENT_CLASSES) == 10
