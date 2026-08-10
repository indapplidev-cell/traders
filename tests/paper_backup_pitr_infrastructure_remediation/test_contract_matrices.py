from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta

import pytest

from app.engine_paper import backup_pitr_infrastructure as infra


def _backup_preflight(case: int) -> infra.PaperProductionBackupPreflight:
    flags = [bool(case & (1 << index)) for index in range(10)]
    return infra.PaperProductionBackupPreflight(
        environment_identity="PRODUCTION" if flags[0] else "ISOLATED",
        postgresql_major=16 if flags[1] else 15,
        schema_head="0008_engine_orchestrator_freshness_retry" if flags[2] else "0007",
        destination_approved=flags[3], destination_persistent=flags[4],
        capacity_sufficient=flags[5], tooling_present=flags[6],
        policy_approved=flags[7], operator_authorized=flags[8],
        valid_backup_age_known=flags[9], pitr_state_known=True,
        protected_binding_access_count=0,
    )


@pytest.mark.parametrize("case", range(1024))
def test_backup_preflight_complete_boolean_matrix_fails_closed(case: int) -> None:
    result = _backup_preflight(case).evaluate()
    assert result.checks_run == 11
    assert result.passed is (case == 1023)
    assert result.passed is (not result.failed_checks)


@pytest.mark.parametrize("case", range(512))
def test_restore_preflight_complete_boolean_matrix_and_production_rejection(case: int) -> None:
    flags = [bool(case & (1 << index)) for index in range(9)]
    request = infra.PaperProductionRestorePreflight(
        artifact_exists=flags[0], checksum_manifest_valid=flags[1],
        engine_compatible=flags[2], schema_metadata_valid=flags[3],
        isolated_target=flags[4], capacity_sufficient=flags[5],
        reconciliation_available=flags[6], operator_authorized=flags[7],
        production_target_requested=flags[8],
    )
    result = request.evaluate()
    expected = all(flags[:8]) and not flags[8]
    assert result.passed is expected
    assert result.production_target_rejected is flags[8]
    assert result.failed_check_count == sum(not value for value in (*flags[:8], not flags[8]))


@pytest.mark.parametrize("case", range(32))
def test_atomic_publication_all_failure_boundaries_never_publish_partial(case: int) -> None:
    flags = [bool(case & (1 << index)) for index in range(5)]
    result = infra.PaperProductionBackupPublicationResult.evaluate(
        tool_completed=flags[0], checksum_verified=flags[1],
        manifest_verified=flags[2], capacity_ready=flags[3],
        atomic_rename_completed=flags[4],
    )
    assert result.partial_artifact_published is False
    assert (result.state is infra.PublicationState.PUBLISHED) is all(flags)
    if not all(flags):
        assert result.failure_code in {
            "TOOL_FAILURE", "CHECKSUM_MISMATCH", "MANIFEST_MISMATCH",
            "DESTINATION_CAPACITY_FAILURE", "ATOMIC_PUBLISH_FAILURE",
        }


@pytest.mark.parametrize("case", range(64))
def test_integrity_policy_rejects_every_disabled_control(case: int) -> None:
    values = [bool(case & (1 << index)) for index in range(6)]
    kwargs = dict(zip((field.name for field in infra.fields(infra.PaperProductionBackupIntegrityPolicy)), values))
    if all(values):
        assert infra.PaperProductionBackupIntegrityPolicy(**kwargs)
    else:
        with pytest.raises(ValueError, match="INTEGRITY_CONTROL_DISABLED"):
            infra.PaperProductionBackupIntegrityPolicy(**kwargs)


def test_recovery_objectives_are_proposed_not_self_approved() -> None:
    policy = infra.PROPOSED_RECOVERY_OBJECTIVES
    assert policy.target_rpo == timedelta(minutes=15)
    assert policy.target_rto == timedelta(hours=2)
    assert policy.maximum_backup_age == timedelta(hours=24)
    assert policy.restore_rehearsal_cadence == timedelta(days=30)
    assert policy.pitr_rehearsal_cadence == timedelta(days=90)
    approval = infra.PaperProductionRecoveryObjectiveApproval(
        policy, False, "recovery-approval-authority"
    )
    assert not approval.approved
    with pytest.raises(FrozenInstanceError):
        policy.status = "APPROVED"


def test_capacity_formula_is_exact_and_unknown_fails_unproven() -> None:
    assert infra.PaperProductionCapacityAssessment(None, None, None).readiness is infra.Readiness.UNPROVEN
    assessment = infra.PaperProductionCapacityAssessment(100, 250, 350)
    assert assessment.required_free_space_bytes == 350
    assert assessment.readiness is infra.Readiness.READY
    assert replace(assessment, available_bytes=349).readiness is infra.Readiness.NOT_READY


@pytest.mark.parametrize(
    "intact,corrupt,backup,pitr,expected",
    [
        (True, False, False, False, infra.RecoveryDecision.FORWARD_FIX),
        (False, True, True, False, infra.RecoveryDecision.RESTORE),
        (False, True, False, True, infra.RecoveryDecision.PITR),
        (False, True, False, False, infra.RecoveryDecision.HARD_INCIDENT),
    ],
)
def test_recovery_decision_tree(intact, corrupt, backup, pitr, expected) -> None:
    assert infra.recovery_decision(
        database_intact=intact, data_corrupted_or_lost=corrupt,
        valid_backup=backup, pitr_available=pitr,
    ) is expected


def test_operator_roles_and_monitoring_matrix_complete_but_unapproved() -> None:
    assert infra.PROPOSED_OPERATOR_OWNERSHIP.complete
    assert not infra.PROPOSED_OPERATOR_OWNERSHIP.approved
    assert infra.PROPOSED_MONITORING_POLICY.complete
    assert not infra.PROPOSED_MONITORING_POLICY.implemented_or_accepted
    assert any(role.two_person_gate for role in infra.PROPOSED_OPERATOR_OWNERSHIP.roles)


def test_retention_contract_protects_last_good_and_wal_base() -> None:
    policy = infra.PaperProductionRetentionPolicy(
        minimum_retained_full_backups=2, minimum_pitr_window=timedelta(days=7),
        maximum_artifact_age=timedelta(days=35), cleanup_safety_floor=2,
        never_delete_last_known_good=True, never_delete_base_required_by_wal=True,
        bounded_deletion_batch=10, dry_run_before_cleanup=True, approved=False,
    )
    assert not policy.approved


def test_restore_procedure_and_postflight_require_reconciliation_and_authorization() -> None:
    assert infra.PaperProductionRestoreProcedure().complete
    result = infra.PaperProductionRestorePostflight(True, True, True, True)
    assert result.passed
    assert not replace(result, reconciliation_healthy=False).passed
    assert not replace(result, explicit_resume_authorization=False).passed
