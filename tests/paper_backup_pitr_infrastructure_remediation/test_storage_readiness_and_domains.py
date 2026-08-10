from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_paper import backup_pitr_infrastructure as infra


def _destination(**changes):
    base = infra.PaperProductionBackupDestinationIdentity(
        opaque_identity="approved-backup-destination",
        storage_class=infra.StorageClass.OBJECT_STORAGE,
        persistence_class=infra.PersistenceClass.MANAGED_PERSISTENT_STORAGE,
        outside_postgres_data_directory=True,
        outside_ephemeral_container_layer=True,
        outside_git_repository=True,
        outside_project_temp=True,
        retention_bounded=True,
        approved_for_backup_restore=True,
    )
    return replace(base, **changes)


@pytest.mark.parametrize("field", (
    "outside_postgres_data_directory", "outside_ephemeral_container_layer",
    "outside_git_repository", "outside_project_temp", "retention_bounded",
    "approved_for_backup_restore",
))
def test_destination_rejects_each_boundary_violation(field: str) -> None:
    destination = _destination(**{field: False})
    assert not destination.valid
    assert infra.storage_readiness(
        destination, capacity_ready=True, access_control_ready=True,
        retention_ready=True,
    ).readiness is infra.Readiness.NOT_READY


@pytest.mark.parametrize("persistence", tuple(infra.PersistenceClass))
def test_only_persistent_destination_classes_can_be_valid(persistence) -> None:
    destination = _destination(persistence_class=persistence)
    expected = persistence in {
        infra.PersistenceClass.PERSISTENT_EXTERNAL_VOLUME,
        infra.PersistenceClass.PERSISTENT_HOST_BIND,
        infra.PersistenceClass.MANAGED_PERSISTENT_STORAGE,
    }
    assert destination.valid is expected


def test_storage_policy_is_immutable_complete_and_secret_free() -> None:
    policy = infra.PaperProductionBackupStoragePolicy(
        storage_class=infra.StorageClass.OBJECT_STORAGE,
        persistence_class=infra.PersistenceClass.MANAGED_PERSISTENT_STORAGE,
        encryption_at_rest_required=True,
        access_control_class=infra.AccessControlClass.PROPOSED_NOT_APPROVED,
        retention_class=infra.RetentionClass.PROPOSED_BOUNDED,
        capacity_floor_bytes=100, minimum_free_space_bytes=200,
        atomic_publish_required=True, partial_artifact_quarantine_or_removal=True,
        manifest_checksum_required=True, owner_role_class="backup-operator",
    )
    assert policy.minimum_free_space_bytes == 200
    with pytest.raises(ValueError, match="UNSAFE_TEXT"):
        replace(policy, owner_role_class="".join(("postgresql", "://", "user", "@example")))


def _finding(index: int, readiness: infra.Readiness, severity: infra.Severity):
    return infra.PaperProductionBackupPitrInfrastructureFinding(
        code=f"B{index}", domain=f"domain-{index}", readiness=readiness,
        severity=severity, evidence="safe-enum-evidence", blocker="remaining-control",
        remediation="controlled-change", closure_condition="approved-proof",
    )


def _domains():
    states = (
        infra.Readiness.READY, infra.Readiness.NOT_READY, infra.Readiness.READY,
        infra.Readiness.NOT_READY, infra.Readiness.READY, infra.Readiness.READY,
        infra.Readiness.UNPROVEN, infra.Readiness.NOT_READY, infra.Readiness.READY,
        infra.Readiness.NOT_READY, infra.Readiness.NOT_READY, infra.Readiness.NOT_READY,
        infra.Readiness.NOT_READY, infra.Readiness.READY, infra.Readiness.READY,
    )
    return tuple(
        infra.PaperProductionBackupPitrInfrastructureDomain(
            f"B{index}", f"domain-{index}", state,
            (_finding(index, state, infra.Severity.CRITICAL if index in {1, 2, 7, 8} else infra.Severity.HIGH),),
        )
        for index, state in enumerate(states, 1)
    )


def test_partial_readiness_cannot_close_blocker() -> None:
    plan = infra.PaperProductionBackupPitrInfrastructureRemediationPlan(
        required_changes=("persistent-backup-destination", "wal-archive-configuration"),
        mutation_classes=(infra.MutationClass.EXTERNAL_STORAGE_REQUIRED,
                          infra.MutationClass.POSTGRES_RESTART_REQUIRED),
        recommended_next_task="controlled-infrastructure-change",
    )
    result = infra.PaperProductionBackupPitrInfrastructureReadinessResult(
        overall_readiness=infra.Readiness.NOT_READY, domains=_domains(),
        backup_mechanism=infra.Readiness.READY, storage=infra.Readiness.NOT_READY,
        restore_applicability=infra.Readiness.READY, pitr_config=infra.Readiness.UNPROVEN,
        archive_persistence=infra.Readiness.NOT_READY,
        rpo_rto_approval=infra.Readiness.NOT_READY,
        operator_ownership=infra.Readiness.NOT_READY,
        capacity=infra.Readiness.UNPROVEN, monitoring=infra.Readiness.NOT_READY,
        critical_blockers=4, high_blockers=5, blocker_closed=False,
        remediation_plan=plan,
    )
    assert not result.blocker_closed
    assert len(result.domains) == 15
    with pytest.raises(ValueError, match="BLOCKER_CLOSED_WITHOUT_ALL_PROOFS"):
        replace(result, blocker_closed=True)


def test_pitr_remediation_specification_is_complete_and_not_applied() -> None:
    plan = infra.PaperProductionPitrRemediationPlan(
        True, True, True, True, True, True, True, True, True, True, True,
        (infra.MutationClass.POSTGRES_RESTART_REQUIRED,
         infra.MutationClass.EXTERNAL_STORAGE_REQUIRED),
    )
    assert plan.complete_specification
    assert not plan.applied
