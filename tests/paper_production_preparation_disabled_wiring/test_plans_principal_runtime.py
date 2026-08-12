from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from app.engine_paper.production_composition import (
    EXPECTED_SCHEMA_HEAD,
    OBSERVABILITY_EVENTS,
    PaperDatabaseOperation,
    PaperProductionDatabasePrincipalPolicy,
    PaperProductionDeploymentPlan,
    PaperProductionFirstCanaryPlan,
    PaperProductionMigrationOrchestrator,
    PaperProductionMigrationPlan,
    PaperProductionMigrationPostflight,
    PaperProductionMigrationPreflight,
    PaperProductionMigrationPreparation,
    PaperProductionMutationBudget,
    PaperProductionPreparationPhase,
    PaperProductionPreparationPlan,
    PaperProductionPrincipalPreflight,
    PaperProductionPrincipalState,
    PaperProductionIdempotencyAction,
    PaperProductionResumeDecision,
    PaperProductionRuntimeDeploymentConfig,
    PaperProductionRuntimeTargetIdentity,
    runtime_configuration_fingerprint,
    safe_structured_event,
)
from app.engine_safety.paper_production_control import PersistentState


@pytest.mark.parametrize("repeat", range(128))
def test_preparation_plan_is_exact_ordered_cancellable_non_destructive(repeat):
    plan = PaperProductionPreparationPlan()
    assert repeat >= 0
    assert plan.phases == tuple(PaperProductionPreparationPhase)
    assert plan.cancellation_between_phases
    assert not plan.automatic_continue_after_partial_phase
    assert not plan.destructive_rollback
    with pytest.raises(FrozenInstanceError):
        plan.destructive_rollback = True


@pytest.mark.parametrize("repeat", range(96))
def test_migration_plan_is_exact_0008_to_0012_forward_only(repeat):
    plan = PaperProductionMigrationPlan()
    assert repeat >= 0
    assert plan.revisions == (
        "0009_paper_trading_persistence_foundation",
            "0010_paper_final_approval_and_order_transition_event_vocabulary",
            "0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
            "0012_paper_account_baseline",
            EXPECTED_SCHEMA_HEAD,
    )
    assert not plan.automatic_downgrade
    assert "PRESERVE_DB" in plan.failure_policy
    assert plan.lock_timeout_ms < plan.statement_timeout_ms


@pytest.mark.parametrize("field", ("exact_start_schema", "pitr_pass", "wal_pass", "kill_switch_disabled", "runtime_stopped", "zero_paper_processes", "backup_catalog_valid"))
@pytest.mark.parametrize("repeat", range(16))
def test_each_migration_preflight_condition_fails_closed(field, repeat):
    good = PaperProductionMigrationPreflight(True, True, True, True, True, True, True)
    assert repeat >= 0 and good.passed
    assert not replace(good, **{field: False}).passed


class FakeExecutor:
    def __init__(self, *, start="0008_engine_orchestrator_freshness_retry", fail=None,
                 final_override=None, reconcile=True, health=True):
        self.revision = start
        self.fail = fail
        self.final_override = final_override
        self.reconciliation = reconcile
        self.healthy = health
        self.applied = []
        self.downgrades = 0

    def apply(self, revision, lock_timeout_ms, statement_timeout_ms):
        if self.fail == revision:
            raise RuntimeError(f"injected {revision}")
        assert lock_timeout_ms == 5_000 and statement_timeout_ms == 60_000
        self.revision = revision
        self.applied.append(revision)

    def current_revision(self):
        return self.final_override or self.revision

    def reconcile(self):
        return self.reconciliation

    def health(self):
        return self.healthy


class InjectedMigrationExecutor(FakeExecutor):
    def __init__(self, exception):
        super().__init__()
        self.exception = exception

    def apply(self, revision, lock_timeout_ms, statement_timeout_ms):
        raise self.exception


def preparation(**changes):
    value = PaperProductionMigrationPreparation(
        PaperProductionMigrationPlan(),
        PaperProductionMigrationPreflight(True, True, True, True, True, True, True),
        "ISOLATED_POSTGRESQL_16", True,
    )
    return replace(value, **changes)


@pytest.mark.parametrize("repeat", range(96))
def test_isolated_orchestrator_success_is_bounded_and_leaves_disabled(repeat):
    executor = FakeExecutor()
    result = PaperProductionMigrationOrchestrator().run_isolated(preparation(), executor)
    assert repeat >= 0
    assert result.completed_revisions == PaperProductionMigrationPlan().revisions
    assert result.final_revision == EXPECTED_SCHEMA_HEAD
    assert result.postflight.passed and not result.stopped
    assert executor.downgrades == 0


FAULTS = (
    "0009_paper_trading_persistence_foundation",
    "0010_paper_final_approval_and_order_transition_event_vocabulary",
    "0011_paper_close_causal_boundary_and_exit_evaluation_cursor",
    EXPECTED_SCHEMA_HEAD,
)


@pytest.mark.parametrize("fault", FAULTS)
@pytest.mark.parametrize("repeat", range(32))
def test_each_revision_failure_stops_preserves_prefix_and_never_downgrades(fault, repeat):
    executor = FakeExecutor(fail=fault)
    result = PaperProductionMigrationOrchestrator().run_isolated(preparation(), executor)
    assert repeat >= 0
    assert result.stopped and result.failure_code
    assert fault not in result.completed_revisions
    assert executor.downgrades == 0


@pytest.mark.parametrize("fault", (
    TimeoutError("lock timeout"), TimeoutError("statement timeout"),
    ConnectionError("connection loss"), RuntimeError("0009 failure"),
    RuntimeError("0010 failure"), RuntimeError("0011 failure"),
))
@pytest.mark.parametrize("repeat", range(16))
def test_migration_transport_timeout_and_revision_faults_all_stop_without_downgrade(fault, repeat):
    executor = InjectedMigrationExecutor(fault)
    result = PaperProductionMigrationOrchestrator().run_isolated(preparation(), executor)
    assert repeat >= 0
    assert result.stopped and not result.completed_revisions
    assert executor.downgrades == 0


@pytest.mark.parametrize("kind,executor", (
    ("baseline", FakeExecutor(start="unexpected")),
    ("postflight_head", FakeExecutor(final_override="0010_paper_final_approval_and_order_transition_event_vocabulary")),
    ("reconciliation", FakeExecutor(reconcile=False)),
    ("health", FakeExecutor(health=False)),
))
@pytest.mark.parametrize("repeat", range(24))
def test_baseline_and_postflight_faults_fail_closed_without_cleanup(kind, executor, repeat):
    result = PaperProductionMigrationOrchestrator().run_isolated(preparation(), executor)
    assert repeat >= 0 and kind
    assert result.stopped
    assert executor.downgrades == 0


@pytest.mark.parametrize("repeat", range(64))
def test_cancellation_occurs_between_revisions_and_never_auto_continues(repeat):
    executor = FakeExecutor()
    calls = iter((False, True))
    result = PaperProductionMigrationOrchestrator().run_isolated(
        preparation(), executor, cancelled=lambda: next(calls)
    )
    assert repeat >= 0
    assert result.stopped and result.failure_code == "CANCELLED_BETWEEN_PHASES"
    assert len(result.completed_revisions) == 1
    assert executor.downgrades == 0


@pytest.mark.parametrize("target,owned", (("PRODUCTION", True), ("ISOLATED_POSTGRESQL_16", False), ("wrong", False)))
@pytest.mark.parametrize("repeat", range(24))
def test_orchestrator_cannot_execute_against_production_or_unowned_target(target, owned, repeat):
    assert repeat >= 0
    with pytest.raises(RuntimeError, match="MIGRATION_PREFLIGHT_OR_TARGET_DENIED"):
        PaperProductionMigrationOrchestrator().run_isolated(
            preparation(execution_target=target, task_owned_isolated=owned), FakeExecutor()
        )


@pytest.mark.parametrize("repeat", range(96))
def test_principal_capability_matrix_uses_actual_objects_and_denies_admin(repeat):
    policy = PaperProductionDatabasePrincipalPolicy()
    allowed = {(row.resource, row.operation) for row in policy.capabilities if row.required}
    denied = {(row.resource, row.operation) for row in policy.capabilities if not row.required}
    assert repeat >= 0
    for table in ("candles_1m", "online_pipeline_runs", "paper_execution_commands",
                  "paper_orders", "paper_fills", "paper_positions",
                  "paper_exit_evaluation_cursors", "paper_journal_entries"):
        assert (table, PaperDatabaseOperation.SELECT) in allowed
    assert ("paper_account_baselines", PaperDatabaseOperation.SELECT) in allowed
    for operation in (PaperDatabaseOperation.INSERT, PaperDatabaseOperation.UPDATE,
                      PaperDatabaseOperation.DELETE):
        assert ("paper_account_baselines", operation) in denied
    assert ("DATABASE_CLUSTER", PaperDatabaseOperation.CREATE_ROLE) in denied
    assert ("DATABASE_CLUSTER", PaperDatabaseOperation.GRANT) in denied
    assert ("ALL_TABLES", PaperDatabaseOperation.ALTER) in denied
    assert ("ALL_TABLES", PaperDatabaseOperation.DROP) in denied
    assert not policy.schema_admin and not policy.role_admin and not policy.live_credential_access
    assert len(policy.fingerprint) == 64


@pytest.mark.parametrize("state,expected", (
    (PaperProductionPrincipalState.NOT_DEPLOYED, PaperProductionIdempotencyAction.CREATE_ONCE),
    (PaperProductionPrincipalState.EXACT_POLICY, PaperProductionIdempotencyAction.REUSE_EXACT),
    (PaperProductionPrincipalState.BROADER_GRANTS, PaperProductionIdempotencyAction.DENY_CONFLICT),
    (PaperProductionPrincipalState.CONFLICTING_IDENTITY, PaperProductionIdempotencyAction.DENY_CONFLICT),
))
@pytest.mark.parametrize("repeat", range(24))
def test_principal_creation_is_idempotent_and_broader_grants_fail_closed(state, expected, repeat):
    gate = PaperProductionPrincipalPreflight(state, True, True, True, True, True)
    assert repeat >= 0
    assert gate.action is expected


@pytest.mark.parametrize("field", ("pitr_confirmed", "schema_at_0012", "kill_switch_disabled",
                                    "runtime_stopped", "explicit_operator_authorization"))
@pytest.mark.parametrize("repeat", range(16))
def test_each_future_principal_creation_precondition_is_mandatory(field, repeat):
    gate = PaperProductionPrincipalPreflight(PaperProductionPrincipalState.NOT_DEPLOYED,
                                             True, True, True, True, True)
    assert repeat >= 0
    assert replace(gate, **{field: False}).action is PaperProductionIdempotencyAction.DENY_CONFLICT


@pytest.mark.parametrize("schema,state,config,reconciled,expected", (
    (EXPECTED_SCHEMA_HEAD, PaperProductionPrincipalState.EXACT_POLICY, True, True,
     PaperProductionIdempotencyAction.COMPLETE_NO_ACTION),
    ("0008_engine_orchestrator_freshness_retry", PaperProductionPrincipalState.NOT_DEPLOYED, False, False,
     PaperProductionIdempotencyAction.CONTINUE),
    ("0010_paper_final_approval_and_order_transition_event_vocabulary", PaperProductionPrincipalState.NOT_DEPLOYED, False, False,
     PaperProductionIdempotencyAction.DENY_CONFLICT),
    (EXPECTED_SCHEMA_HEAD, PaperProductionPrincipalState.BROADER_GRANTS, True, True,
     PaperProductionIdempotencyAction.DENY_CONFLICT),
))
@pytest.mark.parametrize("repeat", range(24))
def test_resume_validation_handles_exact_idempotency_and_conflicts(schema, state, config, reconciled, expected, repeat):
    decision = PaperProductionResumeDecision(schema, state, config, reconciled)
    assert repeat >= 0
    assert decision.action is expected


@pytest.mark.parametrize("repeat", range(96))
def test_disabled_runtime_config_and_target_identity_are_non_secret(repeat):
    config = PaperProductionRuntimeDeploymentConfig()
    fingerprint = runtime_configuration_fingerprint(config)
    policy = PaperProductionDatabasePrincipalPolicy()
    identity = PaperProductionRuntimeTargetIdentity(
        "PRODUCTION", "PAPER", EXPECTED_SCHEMA_HEAD, policy.fingerprint,
        "PaperProductionMarketDataInputAdapter:1.0.0",
        "PaperProductionApprovalSourceAdapter:1.0.0",
        "PaperProductionMutationSafetyGate", fingerprint,
    )
    assert repeat >= 0
    assert not config.runtime_enabled and not config.daemon_enabled and not config.scheduler_enabled
    assert config.dry_run and not config.mutation_enabled and not config.live
    assert config.control_state is PersistentState.DISABLED
    assert "://" not in repr(identity)
    assert len(fingerprint) == 64


@pytest.mark.parametrize("repeat", range(64))
def test_first_canary_and_future_mutation_budgets_are_minimal(repeat):
    canary = PaperProductionFirstCanaryPlan()
    budget = PaperProductionMutationBudget()
    deployment = PaperProductionDeploymentPlan()
    assert repeat >= 0
    assert canary.max_commands == canary.max_open_positions == 1
    assert canary.binance_order_calls == 0 and canary.reconciliation_after_canary
    assert canary.no_eligible_approval_behavior == "NO_ELIGIBLE_APPROVAL_ZERO_MUTATION_CLEAN_NO_TRADE"
    assert budget.paper_business_rows == budget.paper_commands == budget.paper_orders == 0
    assert budget.paper_fills == budget.paper_positions == 0
    assert budget.principal_creations == budget.disabled_runtime_publications == 1
    assert not deployment.automatic_start and not deployment.automatic_arm


@pytest.mark.parametrize("event", OBSERVABILITY_EVENTS)
@pytest.mark.parametrize("repeat", range(8))
def test_observability_allowlist_is_minimal_and_safe(event, repeat):
    rendered = safe_structured_event(event, {"reason_code": "SAFE", "count": 0})
    assert repeat >= 0 and event in rendered
    assert "://" not in rendered


@pytest.mark.parametrize("field", ("password", "secret_value", "credential", "database_url", "dsn", "protected_binding"))
@pytest.mark.parametrize("repeat", range(16))
def test_structured_logging_rejects_secret_shaped_fields(field, repeat):
    assert repeat >= 0
    with pytest.raises(ValueError, match="SECRET_SHAPED_LOG_FIELD_DENIED"):
        safe_structured_event("fault_error", {field: "redacted"})
