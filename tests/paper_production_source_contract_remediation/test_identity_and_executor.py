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
    PaperProductionExecutionAuthorization,
    PaperProductionIdentityError,
    PaperProductionPreparationExecutor,
    PaperProductionPreparationMutationBudget,
    PaperProductionPreparationReadiness,
    PaperProductionTargetGuard,
    PaperPreparationOperationResult,
)
from app.engine_paper.accounting import PaperAccountBaseline
from app.server_api.errors import ApiError
from app.server_api.services.paper_reporting import PaperReadonlyReportingService


VALID = {
    "PAPER_PRODUCTION_ACCOUNT_ID": "PAPER-PROD-PRIMARY",
    "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "PAPER-PROD-LIFECYCLE-01",
    "PAPER_PRODUCTION_CURRENCY": "USDT",
}


class Backend:
    def __init__(self, state="ABSENT", binding=False):
        self.state = state
        self.binding = binding
        self.calls = []

    def validate_target(self, target):
        self.calls.append(("target", target.database_target_id))
        return True

    def inspect_runtime_role(self):
        self.calls.append(("inspect",))
        return self.state

    def inspect_privilege_drift(self):
        self.calls.append(("drift",))
        return self.state == "BROADER_THAN_CONTRACT"

    def ensure_runtime_role(self):
        self.calls.append(("role",))
        changed = self.state == "ABSENT"
        self.state = "EXACT"
        return PaperPreparationOperationResult(changed)

    def reconcile_runtime_grants(self):
        self.calls.append(("runtime_grants",))
        return PaperPreparationOperationResult(True)

    def reconcile_readonly_grants(self):
        self.calls.append(("readonly_grants",))
        return PaperPreparationOperationResult(True)

    def ensure_runtime_binding(self):
        changed = not self.binding
        self.binding = True
        self.calls.append(("binding",))
        return PaperPreparationOperationResult(changed)

    def validate_runtime_binding(self):
        self.calls.append(("validate",))
        return self.binding

    def deploy_disabled_runtime(self):
        self.calls.append(("disabled",))
        return PaperPreparationOperationResult(True)

    def deploy_readonly_api_narrow(self):
        self.calls.append(("readonly",))
        return PaperPreparationOperationResult(True)


def identity():
    return PaperProductionAccountIdentityBinding.from_configuration(VALID)


TARGET = PaperProductionTargetGuard(database_target_id="production-primary")
AUTH = PaperProductionExecutionAuthorization(
    "I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS", ALL_PREPARATION_ACTIONS)


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
    backend = Backend()
    result = PaperProductionPreparationExecutor(backend).plan(identity())
    assert result.finding is PaperPreparationFinding.READY
    assert result.executed_actions == () and result.production_mutations == 0
    assert backend.calls == [] and not backend.binding


def test_missing_identity_is_an_explicit_dry_run_finding():
    result = PaperProductionPreparationExecutor(Backend()).plan(None)
    assert result.finding is PaperPreparationFinding.IDENTITY_BINDING_MISSING


def test_executor_binds_and_never_has_or_returns_secret_surface():
    backend = Backend()
    result = PaperProductionPreparationExecutor(backend).execute(
        identity(), TARGET, PaperProductionPreparationMutationBudget(), AUTH)
    rendered = repr(result) + str(result.safe_dict())
    assert result.finding is PaperPreparationFinding.READY
    assert backend.binding
    assert "://" not in rendered
    assert not ({"password", "secret", "credential", "uri", "dsn"} & set(result.safe_dict()))


def test_existing_exact_role_and_binding_take_idempotent_ensure_paths():
    backend = Backend("EXACT", True)
    result = PaperProductionPreparationExecutor(backend).execute(
        identity(), TARGET, PaperProductionPreparationMutationBudget(), AUTH)
    assert result.finding is PaperPreparationFinding.READY
    assert sum(call[0] == "role" for call in backend.calls) == 1
    assert sum(call[0] == "binding" for call in backend.calls) == 1


def test_broader_role_fails_closed_without_revoke_or_mutation():
    backend = Backend("BROADER_THAN_CONTRACT", True)
    result = PaperProductionPreparationExecutor(backend).execute(
        identity(), TARGET, PaperProductionPreparationMutationBudget(), AUTH)
    assert result.finding is PaperPreparationFinding.EXISTING_ROLE_PRIVILEGE_DRIFT
    assert result.executed_actions == ()
    assert backend.calls == [("target", "production-primary"), ("drift",)]


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
        PaperProductionTargetGuard(database_target_id="production-primary", environment="STAGING")
    with pytest.raises(ValueError):
        PaperProductionPreparationMutationBudget(max_runtime_role_create=2)


def test_exception_is_sanitized():
    class Exploding(Backend):
        def inspect_runtime_role(self):
            raise RuntimeError("postgresql" + "://user:password@host/db")
    with pytest.raises(RuntimeError) as caught:
        PaperProductionPreparationExecutor(Exploding()).execute(
            identity(), TARGET, PaperProductionPreparationMutationBudget(), AUTH)
    assert str(caught.value) == "PAPER_PRODUCTION_PREPARATION_SAFE_FAILURE"
    assert caught.value.__cause__ is None


def test_readiness_reports_each_preparation_gap_and_never_false_positive():
    value = PaperProductionPreparationReadiness(False, False, False, False, False, False, False, False)
    assert not value.current_mutation_ready
    assert set(value.findings) == {
        PaperPreparationFinding.IDENTITY_BINDING_MISSING,
        PaperPreparationFinding.PROTECTED_BACKEND_MISSING,
        PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING,
        PaperPreparationFinding.RUNTIME_GRANTS_NOT_READY,
        PaperPreparationFinding.READONLY_GRANTS_NOT_READY,
        PaperPreparationFinding.SCHEMA_NOT_READY,
        PaperPreparationFinding.BASELINE_MISSING,
        PaperPreparationFinding.READONLY_REPORTING_NOT_DEPLOYED,
    }
    assert PaperProductionPreparationReadiness(True, True, True, True, True, True, True, True).current_mutation_ready


class ReportingRepository:
    def __init__(self, baseline):
        self.baseline = baseline
    def schema_revision(self): return "0015_trading_universe_activation"
    def schema_revisions(self): return ("0015_trading_universe_activation",)
    def paper_schema_contract(self):
        from app.server_api.schema_compatibility import PaperSchemaContractResult
        return PaperSchemaContractResult(True)
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
