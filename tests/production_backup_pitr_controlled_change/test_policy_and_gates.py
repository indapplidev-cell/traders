from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.engine_safety import production_backup as backup


@pytest.mark.parametrize("case", range(2048))
def test_future_paper_backup_pitr_gate_complete_boolean_matrix(case: int) -> None:
    flags = [bool(case & (1 << index)) for index in range(11)]
    failed = tuple(
        name for name, enabled in zip(
            (
                "NO_VALID_LOGICAL_BACKUP", "LOGICAL_BACKUP_TOO_OLD",
                "MIN_LOGICAL_BACKUPS_NOT_MET", "BASE_BACKUP_MISSING",
                "WAL_ARCHIVE_NOT_PROGRESSING", "WAL_ARCHIVE_FAILURE",
                "PITR_WINDOW_BELOW_TARGET", "CATALOG_INCONSISTENT",
                "BACKUP_DESTINATION_LOW_SPACE", "RESTORE_REHEARSAL_MISSING",
            ),
            flags[:10], strict=True,
        ) if enabled
    )
    health = backup.BackupPitrHealth(
        ready=not failed, logical_backup_count=2, last_valid_logical_backup_age_seconds=0,
        logical_backup_bootstrap_exception=False, valid_base_backup=True,
        wal_archive_progressing=True, wal_archive_failure_count=0,
        pitr_window_seconds=86400, catalog_healthy=True,
        destination_free_space_bytes=10 * 1024**3,
        last_restore_rehearsal_age_seconds=0, last_pitr_rehearsal_age_seconds=0,
        failed_gates=failed,
    )
    assert backup.future_paper_enablement_gate(
        health, reconciliation_available=flags[10]
    ) is (not failed and flags[10])


@pytest.mark.parametrize("case", range(128))
def test_recovery_policy_rejects_each_invalid_numeric_combination(case: int) -> None:
    values = [15, 120, 24, 2, 24, 30, 90]
    for index in range(7):
        if case & (1 << index):
            values[index] = 0
    kwargs = dict(zip(
        (
            "target_rpo_minutes", "target_rto_minutes",
            "max_logical_backup_age_hours", "min_valid_logical_backups",
            "min_pitr_window_hours", "restore_rehearsal_cadence_days",
            "pitr_rehearsal_cadence_days",
        ), values, strict=True,
    ))
    if case:
        with pytest.raises(ValueError, match="INVALID_RECOVERY_POLICY"):
            backup.RecoveryPolicy(**kwargs)
    else:
        assert backup.RecoveryPolicy(**kwargs) == backup.POLICY


def test_technical_policy_is_exact_and_local_role_bound() -> None:
    assert backup.TARGET_RPO == timedelta(minutes=15)
    assert backup.TARGET_RTO == timedelta(hours=2)
    assert backup.MAX_LOGICAL_BACKUP_AGE == timedelta(hours=24)
    assert backup.MIN_VALID_LOGICAL_BACKUPS == 2
    assert backup.MIN_PITR_WINDOW == timedelta(hours=24)
    assert backup.PROJECT_OPERATOR_ROLE == "TRADERS_LOCAL_OPERATOR"
    assert backup.RECOVERY_APPROVAL_ROLE == "TRADERS_LOCAL_OPERATOR"
    assert backup.POLICY.two_person_approval_required_for_paper is False


def test_task_baseline_and_required_evidence_are_exact() -> None:
    assert backup.TASK_BASE_HEAD == "3e4ec00ee2a6f7a24dceb93f00f14a8890e0fd34"
    assert backup.TASK_BASE_TREE == "ff790a81f9b017ed21825f488c9811e040172c33"
    assert len(backup.REQUIRED_EVIDENCE_HASHES) == 7
    assert all(len(value) == 64 for value in backup.REQUIRED_EVIDENCE_HASHES.values())


def test_health_bootstrap_allows_one_fresh_backup_but_not_missing_base(tmp_path) -> None:
    for name in ("logical", "base", "wal_archive", "catalog/manifests"):
        (tmp_path / name).mkdir(parents=True)
    health = backup.evaluate_health(
        root=tmp_path, now=datetime.now(timezone.utc), wal_archive_progressing=True,
        wal_archive_failure_count=0, pitr_window=timedelta(hours=24),
        last_restore_rehearsal=datetime.now(timezone.utc),
        last_pitr_rehearsal=datetime.now(timezone.utc),
    )
    assert not health.ready
    assert "NO_VALID_LOGICAL_BACKUP" in health.failed_gates
    assert "BASE_BACKUP_MISSING" in health.failed_gates


def test_future_gate_fails_when_reconciliation_unavailable() -> None:
    health = backup.BackupPitrHealth(
        True, 1, 0, True, True, True, 0, 86400, True, 10 * 1024**3,
        0, 0, (),
    )
    assert not backup.future_paper_enablement_gate(health, reconciliation_available=False)
    assert backup.future_paper_enablement_gate(health, reconciliation_available=True)
