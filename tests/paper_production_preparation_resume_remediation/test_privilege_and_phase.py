from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.engine_paper.production_preparation import (
    ALL_PREPARATION_ACTIONS,
    EXPECTED_FINAL_ALEMBIC,
    EXPECTED_START_ALEMBIC,
    SUPPORTED_PREPARATION_REVISIONS,
    READONLY_ACCEPTED_GRANTS,
    READONLY_BASELINE_GRANTS,
    READONLY_GRANTS,
    PaperPreparationAction,
    PaperPreparationOperationResult,
    PaperPreparationPhase,
    PaperProductionAccountIdentityBinding,
    PaperProductionExecutionAuthorization,
    PaperProductionPreparationExecutor,
    PaperProductionPreparationMutationBudget,
    PaperProductionTargetGuard,
    classify_database_privilege_drift,
    classify_preparation_phase,
    normalize_database_grants,
    required_database_privileges_present,
)
from app.engine_paper.production_preparation_cli import _execute


def _rows(grants):
    return tuple((grant.table, operation, "NO") for grant in grants for operation in grant.operations)


@pytest.mark.parametrize("operation", [
    "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER",
])
def test_unexpected_readonly_write_or_table_ddl_fails_closed(operation):
    rows = _rows(READONLY_BASELINE_GRANTS) + (("candles_15m", operation, "NO"),)
    assert classify_database_privilege_drift(rows, READONLY_ACCEPTED_GRANTS)


def test_legitimate_baseline_and_paper_select_sets_are_accepted_and_normalized():
    baseline = _rows(READONLY_BASELINE_GRANTS)
    combined = _rows(READONLY_ACCEPTED_GRANTS)
    assert not classify_database_privilege_drift(baseline, READONLY_ACCEPTED_GRANTS)
    assert not classify_database_privilege_drift(combined, READONLY_ACCEPTED_GRANTS)
    assert normalize_database_grants(combined) == normalize_database_grants(tuple(reversed(combined)))
    assert normalize_database_grants(combined + combined) == normalize_database_grants(combined)


def test_grant_option_ownership_membership_and_non_table_acl_fail_closed():
    baseline = _rows(READONLY_BASELINE_GRANTS)
    assert classify_database_privilege_drift(
        baseline + (("candles_15m", "SELECT", "YES"),), READONLY_ACCEPTED_GRANTS)
    assert classify_database_privilege_drift(baseline, READONLY_ACCEPTED_GRANTS, ownership=1)
    assert classify_database_privilege_drift(baseline, READONLY_ACCEPTED_GRANTS, memberships=1)
    assert classify_database_privilege_drift(baseline, READONLY_ACCEPTED_GRANTS, non_table_acl=1)


def test_missing_paper_select_is_not_drift_but_is_not_the_complete_grant_set():
    baseline = _rows(READONLY_BASELINE_GRANTS)
    assert not classify_database_privilege_drift(baseline, READONLY_ACCEPTED_GRANTS)
    assert normalize_database_grants(baseline) != normalize_database_grants(_rows(READONLY_GRANTS))
    assert required_database_privileges_present(baseline, READONLY_BASELINE_GRANTS)
    assert not required_database_privileges_present(baseline[:-1], READONLY_BASELINE_GRANTS)


@pytest.mark.parametrize(("revision", "complete", "drift", "expected"), [
    (EXPECTED_START_ALEMBIC, False, False, PaperPreparationPhase.PRE_MIGRATION_READY),
    (EXPECTED_FINAL_ALEMBIC, False, False, PaperPreparationPhase.PARTIAL_RESUMABLE),
    (EXPECTED_FINAL_ALEMBIC, True, False, PaperPreparationPhase.COMPLETED),
    ("unexpected", False, False, PaperPreparationPhase.INCOMPATIBLE),
    (EXPECTED_FINAL_ALEMBIC, False, True, PaperPreparationPhase.INCOMPATIBLE),
])
def test_phase_is_schema_and_postcondition_aware(revision, complete, drift, expected):
    assert classify_preparation_phase(
        revision, preparation_complete=complete, privilege_drift=drift,
    ) is expected


def test_production_upgrade_contract_accepts_deployed_0018_through_0024() -> None:
    assert "0018_promote_5m_production_search" in SUPPORTED_PREPARATION_REVISIONS
    assert "0019_first_class_15m_domain" in SUPPORTED_PREPARATION_REVISIONS
    assert EXPECTED_FINAL_ALEMBIC == "0029_stale_position_shadow"


def test_non_orchestrated_resume_targets_the_current_supported_revision() -> None:
    captured = []
    backend = SimpleNamespace(current_revision=lambda: EXPECTED_FINAL_ALEMBIC)
    executor = SimpleNamespace(execute=lambda identity, target, budget, authorization:
                               captured.append(target) or "PASS")
    composition = SimpleNamespace(
        backend=backend, executor=executor, identity=object(),
        target=PaperProductionTargetGuard("production-primary"),
    )
    result = _execute(
        composition, (PaperPreparationAction.DEPLOY_READONLY_API_NARROW,),
        orchestrate=False, balance=None,
    )
    assert result == "PASS"
    assert captured[0].expected_start_alembic == EXPECTED_FINAL_ALEMBIC


class ResumeBackend:
    def __init__(self, satisfied=()):
        self.satisfied = set(satisfied)
        self.calls = []

    def action_satisfied(self, action):
        return action in self.satisfied

    def validate_target(self, target):
        return True

    def inspect_privilege_drift(self):
        return False

    def inspect_runtime_role(self):
        return "EXACT_OR_NARROWER"

    def _operation(self, action):
        self.calls.append(action)
        self.satisfied.add(action)
        return PaperPreparationOperationResult(True)

    def ensure_runtime_role(self): return self._operation(PaperPreparationAction.ENSURE_RUNTIME_ROLE)
    def reconcile_runtime_grants(self): return self._operation(PaperPreparationAction.APPLY_RUNTIME_GRANTS)
    def reconcile_readonly_grants(self): return self._operation(PaperPreparationAction.APPLY_READONLY_REPORTING_GRANTS)
    def ensure_runtime_binding(self): return self._operation(PaperPreparationAction.BIND_RUNTIME_CREDENTIAL)
    def validate_runtime_binding(self):
        self.calls.append(PaperPreparationAction.VALIDATE_RUNTIME_BINDING)
        self.satisfied.add(PaperPreparationAction.VALIDATE_RUNTIME_BINDING)
        return True
    def deploy_disabled_runtime(self): return self._operation(PaperPreparationAction.DEPLOY_DISABLED_RUNTIME_CONFIGURATION)
    def deploy_readonly_api_narrow(self): return self._operation(PaperPreparationAction.DEPLOY_READONLY_API_NARROW)


def test_executor_resume_skips_satisfied_prefix_and_replay_has_zero_mutations():
    prefix = ALL_PREPARATION_ACTIONS[:3]
    backend = ResumeBackend(prefix)
    executor = PaperProductionPreparationExecutor(backend)
    identity = PaperProductionAccountIdentityBinding("PAPER-PRODUCTION-PRIMARY", "PAPER-LIFECYCLE-01")
    authorization = PaperProductionExecutionAuthorization(
        "I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS", ALL_PREPARATION_ACTIONS,
    )
    first = executor.execute(identity, PaperProductionTargetGuard("production-primary"),
                             PaperProductionPreparationMutationBudget(), authorization)
    assert tuple(backend.calls) == ALL_PREPARATION_ACTIONS[3:]
    assert first.production_mutations == 3  # validation is read-only
    backend.calls.clear()
    second = executor.execute(identity, PaperProductionTargetGuard("production-primary"),
                              PaperProductionPreparationMutationBudget(), authorization)
    assert backend.calls == []
    assert second.production_mutations == 0
