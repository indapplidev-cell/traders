from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.engine_paper.production_preparation import (
    ALL_PREPARATION_ACTIONS,
    READONLY_GRANTS,
    RUNTIME_GRANTS,
    PaperPreparationAction,
    PaperPreparationFinding,
    PaperProductionAccountIdentityBinding,
    PaperProductionIdentityError,
    PaperProductionPreparationExecutor,
    PaperProductionPreparationMutationBudget,
    PaperProductionPreparationReadiness,
    PaperProductionTargetGuard,
)
from app.engine_paper.accounting import PaperAccountBaseline
from app.server_api.errors import ApiError
from app.server_api.services.paper_reporting import PaperReadonlyReportingService


VALID = {
    "PAPER_PRODUCTION_ACCOUNT_ID": "PAPER-PROD-PRIMARY",
    "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "PAPER-PROD-LIFECYCLE-01",
    "PAPER_PRODUCTION_CURRENCY": "USDT",
}


class Binding:
    def __init__(self, present=False):
        self.present = present
        self.stores = 0
        self.value = None

    def binding_present(self):
        return self.present

    def store_runtime_credential(self, role_name, password):
        assert role_name == "traders_paper_runtime"
        self.stores += 1
        self.present = True
        self.value = password


class Backend:
    def __init__(self, state="ABSENT"):
        self.state = state
        self.calls = []

    def inspect_role(self, role_name):
        self.calls.append(("inspect", role_name))
        return self.state

    def ensure_login_role(self, role_name, password, policy):
        assert not any((policy.superuser, policy.createdb, policy.createrole,
                        policy.replication, policy.bypassrls, policy.grant_option,
                        policy.ownership, bool(policy.memberships)))
        self.calls.append(("role", role_name, password))
        self.state = "EXACT"
        return True

    def reconcile_grants(self, role_name, grants):
        self.calls.append(("grants", role_name, grants))
        return True

    def validate_binding(self, role_name):
        self.calls.append(("validate", role_name))
        return True

    def deploy_disabled_runtime(self):
        self.calls.append(("disabled",))
        return True

    def deploy_readonly_api_narrow(self):
        self.calls.append(("readonly",))
        return True


def identity():
    return PaperProductionAccountIdentityBinding.from_configuration(VALID)


def test_identity_is_explicit_canonical_and_stable_across_restart():
    first = identity()
    second = PaperProductionAccountIdentityBinding.from_configuration(dict(VALID))
    assert first == second
    assert first.account_identity().account_id == "PAPER-PROD-PRIMARY"
    assert first.account_identity().accounting_session_id == "PAPER-PROD-LIFECYCLE-01"
    assert first.currency == "USDT"


@pytest.mark.parametrize("mutation", (
    {}, {"PAPER_PRODUCTION_ACCOUNT_ID": ""},
    {"PAPER_PRODUCTION_ACCOUNT_ID": " whitespace "},
    {"PAPER_PRODUCTION_ACCOUNT_ID": "test-fixture"},
    {"PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "new each restart!"},
    {"PAPER_PRODUCTION_CURRENCY": "USD"},
))
def test_identity_fails_closed_for_missing_empty_invalid_or_fixture(mutation):
    values = dict(VALID)
    if not mutation:
        values.pop("PAPER_PRODUCTION_ACCOUNT_ID")
    else:
        values.update(mutation)
    with pytest.raises(PaperProductionIdentityError):
        PaperProductionAccountIdentityBinding.from_configuration(values)


def test_contract_has_no_client_or_random_identity_input():
    names = {field.name for field in fields(PaperProductionAccountIdentityBinding)}
    assert names == {"paper_account_id", "accounting_session_id", "currency", "source"}
    assert not names & {"client", "payload", "request", "random", "uuid"}


def test_dry_run_is_non_mutating_and_does_not_touch_binding():
    backend, binding = Backend(), Binding()
    result = PaperProductionPreparationExecutor(backend, binding).plan(identity())
    assert result.finding is PaperPreparationFinding.READY
    assert result.executed_actions == () and result.production_mutations == 0
    assert backend.calls == [] and binding.stores == 0


def test_missing_identity_is_an_explicit_dry_run_finding():
    result = PaperProductionPreparationExecutor(Backend(), Binding()).plan(None)
    assert result.finding is PaperPreparationFinding.IDENTITY_BINDING_MISSING


def test_executor_generates_binds_and_never_returns_secret():
    backend, binding = Backend(), Binding()
    secret = "S" * 48
    result = PaperProductionPreparationExecutor(backend, binding, lambda _: secret).execute(
        identity(), PaperProductionTargetGuard(), PaperProductionPreparationMutationBudget())
    rendered = repr(result) + str(result.safe_dict())
    assert result.finding is PaperPreparationFinding.READY
    assert binding.value == secret and binding.stores == 1
    assert secret not in rendered and "://" not in rendered
    assert not ({"password", "secret", "credential", "uri", "dsn"} & set(result.safe_dict()))


def test_existing_exact_role_and_binding_is_idempotent():
    backend, binding = Backend("EXACT"), Binding(True)
    result = PaperProductionPreparationExecutor(backend, binding).execute(
        identity(), PaperProductionTargetGuard(), PaperProductionPreparationMutationBudget())
    assert result.finding is PaperPreparationFinding.READY
    assert binding.stores == 0
    assert not any(call[0] == "role" for call in backend.calls)


def test_broader_role_fails_closed_without_revoke_or_mutation():
    backend, binding = Backend("BROADER_THAN_CONTRACT"), Binding(True)
    result = PaperProductionPreparationExecutor(backend, binding).execute(
        identity(), PaperProductionTargetGuard(), PaperProductionPreparationMutationBudget())
    assert result.finding is PaperPreparationFinding.EXISTING_ROLE_PRIVILEGE_DRIFT
    assert result.executed_actions == ()
    assert backend.calls == [("inspect", "traders_paper_runtime")]


def test_allowlists_are_exact_least_privilege():
    runtime = {grant.table: grant.operations for grant in RUNTIME_GRANTS}
    readonly = {grant.table: grant.operations for grant in READONLY_GRANTS}
    assert runtime["paper_account_baselines"] == ("SELECT",)
    assert all("DELETE" not in ops for ops in runtime.values())
    assert all(set(ops) <= {"SELECT", "INSERT", "UPDATE"} for ops in runtime.values())
    assert all(ops == ("SELECT",) for ops in readonly.values())
    assert "paper_first_canary_sessions" in runtime and "paper_account_baselines" in readonly


def test_action_vocabulary_cannot_trade_arm_start_or_enable_live():
    names = " ".join(action.value for action in ALL_PREPARATION_ACTIONS)
    assert not any(word in names for word in ("ARM", "START", "ORDER", "TRADE", "LIVE"))


def test_target_and_budget_are_fixed_and_fail_closed():
    with pytest.raises(ValueError):
        PaperProductionTargetGuard(environment="STAGING")
    with pytest.raises(ValueError):
        PaperProductionPreparationMutationBudget(max_role_create=2)


def test_exception_is_sanitized():
    class Exploding(Backend):
        def inspect_role(self, role_name):
            raise RuntimeError("postgresql://user:password@host/db")
    with pytest.raises(RuntimeError) as caught:
        PaperProductionPreparationExecutor(Exploding(), Binding()).execute(
            identity(), PaperProductionTargetGuard(), PaperProductionPreparationMutationBudget())
    assert str(caught.value) == "PAPER_PRODUCTION_PREPARATION_SAFE_FAILURE"
    assert caught.value.__cause__ is None


def test_readiness_reports_each_preparation_gap_and_never_false_positive():
    value = PaperProductionPreparationReadiness(False, False, False, False, False, False)
    assert not value.current_mutation_ready
    assert set(value.findings) == {
        PaperPreparationFinding.IDENTITY_BINDING_MISSING,
        PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING,
        PaperPreparationFinding.RUNTIME_GRANTS_NOT_READY,
        PaperPreparationFinding.READONLY_GRANTS_NOT_READY,
        PaperPreparationFinding.SCHEMA_NOT_READY,
        PaperPreparationFinding.BASELINE_MISSING,
    }
    assert PaperProductionPreparationReadiness(True, True, True, True, True, True).current_mutation_ready


class ReportingRepository:
    def __init__(self, baseline):
        self.baseline = baseline
    def schema_revision(self): return "0013_paper_first_canary_correlation"
    def list_account_baselines(self, limit): return (self.baseline,)
    def list_closed_trade_facts(self, limit): return ()


def test_readonly_account_and_reconciliation_are_bound_to_production_identity():
    binding = identity()
    baseline = PaperAccountBaseline("baseline:production-paper-v1", binding.account_identity(),
        Decimal("100.00"), datetime(2026, 8, 12, tzinfo=timezone.utc))
    service = PaperReadonlyReportingService(ReportingRepository(baseline), production_identity=binding)
    assert service.account().account_id == binding.paper_account_id
    assert service.reconciliation().overall_status == "HEALTHY"
    other = PaperAccountBaseline("baseline:other", PaperProductionAccountIdentityBinding(
        "PAPER-PROD-OTHER", "PAPER-PROD-LIFECYCLE-02").account_identity(),
        Decimal("100.00"), datetime(2026, 8, 12, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as caught:
        PaperReadonlyReportingService(ReportingRepository(other), production_identity=binding).account()
    assert caught.value.code == "PRODUCTION_IDENTITY_MISMATCH"
