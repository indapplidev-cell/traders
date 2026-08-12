from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
import json

import pytest

from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAction,
    PaperControlledRuntimeTarget,
)
from app.engine_paper.controlled_runtime_canary import (
    CANARY_ACKNOWLEDGEMENT,
    EXPECTED_MIGRATION_HEAD,
    TASK_ID,
    PaperControlledRuntimeCanaryMutationBudget,
    PaperControlledRuntimeCanaryOutcome,
    PaperControlledRuntimeCanaryRowCountDeltas,
    PaperControlledRuntimeCanaryStage,
    PaperControlledRuntimeCanaryTargetIdentity,
    PaperControlledRuntimeSingleCycleCanaryRequest,
    canary_ownership_marker,
    main,
    mutation_budget_matches,
    paper_canary_graph_fingerprint,
    valid_canary_target_identity,
)
from app.engine_paper.controlled_worker import PaperLifecycleCycleScope
from app.engine_safety import ExecutionMode
from tests.paper_controlled_runtime_canary.conftest import NOW, build_canary


@pytest.mark.parametrize("outcome", tuple(PaperControlledRuntimeCanaryOutcome))
def test_all_31_bounded_outcomes_have_stable_canary_prefix(outcome):
    assert outcome.value.startswith("CANARY_")
    assert len(outcome.value) <= 64


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_exact_stage_budget_matches_itself(stage):
    budget = PaperControlledRuntimeCanaryMutationBudget.exact_for_stage(stage)
    delta_values = {
        item.name: getattr(budget, item.name)
        for item in fields(PaperControlledRuntimeCanaryRowCountDeltas)
    }
    assert mutation_budget_matches(
        budget, PaperControlledRuntimeCanaryRowCountDeltas(**delta_values)
    )


_BUDGET_FIELDS = tuple(
    item.name for item in fields(PaperControlledRuntimeCanaryRowCountDeltas)
)


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
@pytest.mark.parametrize("field_name", _BUDGET_FIELDS)
@pytest.mark.parametrize("difference", (-1, 1))
def test_each_stage_budget_rejects_each_under_or_over_delta(
    stage, field_name, difference
):
    budget = PaperControlledRuntimeCanaryMutationBudget.exact_for_stage(stage)
    values = {
        item.name: getattr(budget, item.name)
        for item in fields(PaperControlledRuntimeCanaryRowCountDeltas)
    }
    values[field_name] += difference
    assert not mutation_budget_matches(
        budget, PaperControlledRuntimeCanaryRowCountDeltas(**values)
    )


_FORBIDDEN_DATABASE_NAMES = tuple(
    dict.fromkeys(
        [
            "",
            "postgres",
            "production",
            "traders_ml",
            "paper",
            "paper_test_production",
            "paper_test_prod_runtime",
            "paper_test_shared",
            "paper_test_readonly",
            "paper_test_" + "a" * 60,
            "PAPER_TEST_UPPER",
            "paper-test-hyphen",
            "paper_test_has.dot",
        ]
        + [f"unsafe_{index}" for index in range(40)]
    )
)


@pytest.mark.parametrize("database_name", _FORBIDDEN_DATABASE_NAMES)
def test_target_identity_rejects_each_forbidden_database_name(database_name):
    request, _, _, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND
    )
    identity = replace(request.target_identity, database_name=database_name or "x")
    assert not valid_canary_target_identity(identity)


_FORBIDDEN_ROLE_NAMES = tuple(
    dict.fromkeys(
        [
            "",
            "postgres",
            "traders",
            "production_role",
            "readonly_api",
            "paper_canary_production",
            "paper_canary_shared",
            "paper_canary_readonly",
            "paper_canary_" + "a" * 60,
            "PAPER_CANARY_UPPER",
            "paper-canary-hyphen",
            "paper_canary_has.dot",
        ]
        + [f"unsafe_role_{index}" for index in range(40)]
    )
)


@pytest.mark.parametrize("role_name", _FORBIDDEN_ROLE_NAMES)
def test_target_identity_rejects_each_forbidden_role_name(role_name):
    request, _, _, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND
    )
    identity = replace(request.target_identity, database_role_name=role_name or "x")
    assert not valid_canary_target_identity(identity)


@pytest.mark.parametrize("suffix", tuple(f"case_{index:03d}" for index in range(64)))
def test_target_identity_accepts_bounded_task_owned_names(suffix):
    request, _, _, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND
    )
    database_name = f"paper_test_{suffix}"
    role_name = f"paper_canary_{suffix}"
    identity = replace(
        request.target_identity,
        database_name=database_name,
        database_role_name=role_name,
        ownership_marker=canary_ownership_marker(
            TASK_ID,
            request.canary_run_id,
            database_name,
            role_name,
        ),
    )
    assert valid_canary_target_identity(identity)


@pytest.mark.parametrize(
    "change",
    (
        {"target_kind": PaperControlledRuntimeTarget.CONFIGURATION_ONLY},
        {"task_id": "WRONG_TASK"},
        {"migration_head": "0010_paper_final_approval_authority"},
        {"ownership_marker": "wrong:marker"},
        {"expires_at": NOW},
        {"created_at": NOW + timedelta(hours=2)},
        {"contract_version": "UNSUPPORTED"},
    ),
)
def test_target_identity_rejects_each_structural_mismatch(change):
    request, _, _, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND
    )
    assert not valid_canary_target_identity(replace(request.target_identity, **change))


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_successful_contract_is_immutable_and_slotted(stage):
    request, _, _, _, _ = build_canary(stage)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        request.task_id = "changed"
    assert not hasattr(request, "__dict__")
    assert not hasattr(request.arming, "__dict__")
    assert not hasattr(request.target_identity, "__dict__")
    assert not hasattr(request.expected_mutation_budget, "__dict__")


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
@pytest.mark.parametrize(
    "arming_field,value",
    (
        ("arming_contract_version", "WRONG"),
        ("task_id", "WRONG"),
        ("canary_run_id", "WRONG"),
        ("configuration_id", "WRONG"),
        ("expected_graph_fingerprint", "0" * 64),
        ("single_use", False),
        ("explicit_acknowledgement", "NO"),
    ),
)
def test_every_arming_mismatch_stops_before_worker(stage, arming_field, value):
    request, service, worker, _, _ = build_canary(stage)
    changed = replace(request.arming, **{arming_field: value})
    result = service.run(replace(request, arming=changed))
    assert result.outcome is PaperControlledRuntimeCanaryOutcome.CANARY_ARMING_INVALID
    assert worker.calls == 0
    assert result.worker_invocations == 0


@pytest.mark.parametrize("minutes_expired", tuple(range(1, 33)))
def test_each_expired_arming_stops_before_worker(minutes_expired):
    request, service, worker, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY
    )
    arming = replace(
        request.arming, expires_at=request.evaluated_at - timedelta(minutes=minutes_expired)
    )
    result = service.run(replace(request, arming=arming))
    assert result.outcome is PaperControlledRuntimeCanaryOutcome.CANARY_ARMING_EXPIRED
    assert worker.calls == 0


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_fingerprint_is_deterministic_for_each_stage(stage):
    request, _, _, loader, _ = build_canary(stage)
    values = {
        paper_canary_graph_fingerprint(loader.graph, request.expected_stage)
        for _ in range(20)
    }
    assert values == {request.expected_graph_fingerprint}


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
@pytest.mark.parametrize("different_stage", tuple(PaperControlledRuntimeCanaryStage))
def test_fingerprint_binds_expected_stage(stage, different_stage):
    request, _, _, loader, _ = build_canary(stage)
    fingerprint = paper_canary_graph_fingerprint(loader.graph, different_stage)
    assert (fingerprint == request.expected_graph_fingerprint) is (
        stage is different_stage
    )


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_each_stage_executes_one_worker_and_one_mutating_stage(stage):
    request, service, worker, _, _ = build_canary(stage)
    result = service.run(request)
    assert result.outcome is PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED
    assert worker.calls == 1
    assert result.worker_invocations == 1
    assert result.mutating_stage_invocations == 1
    assert result.mutation_budget_result == "PASS"


@pytest.mark.parametrize(
    "configuration_change,expected",
    (
        (
            {"target": PaperControlledRuntimeTarget.CONFIGURATION_ONLY},
            PaperControlledRuntimeCanaryOutcome.CANARY_TARGET_FORBIDDEN,
        ),
        (
            {"execution_mode": ExecutionMode.LIVE},
            PaperControlledRuntimeCanaryOutcome.CANARY_LIVE_FORBIDDEN,
        ),
        (
            {"execution_mode": ExecutionMode.OFF},
            PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID,
        ),
        (
            {"explicit_paper_authorization": False},
            PaperControlledRuntimeCanaryOutcome.CANARY_PAPER_AUTHORIZATION_MISSING,
        ),
        (
            {"runtime_action": PaperControlledRuntimeAction.EXECUTE},
            PaperControlledRuntimeCanaryOutcome.CANARY_CONFIGURATION_INVALID,
        ),
        (
            {
                "cycle_scope": (
                    PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST
                )
            },
            PaperControlledRuntimeCanaryOutcome.CANARY_SCOPE_INVALID,
        ),
        (
            {"max_stages_per_cycle": 2},
            PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_LIMIT_INVALID,
        ),
        (
            {"network_access_allowed": True},
            PaperControlledRuntimeCanaryOutcome.CANARY_NETWORK_FORBIDDEN,
        ),
        (
            {"polling_allowed": True},
            PaperControlledRuntimeCanaryOutcome.CANARY_POLLING_FORBIDDEN,
        ),
        (
            {"scheduler_allowed": True},
            PaperControlledRuntimeCanaryOutcome.CANARY_SCHEDULER_FORBIDDEN,
        ),
        (
            {"daemon_allowed": True},
            PaperControlledRuntimeCanaryOutcome.CANARY_DAEMON_FORBIDDEN,
        ),
    ),
)
@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_configuration_denial_matrix_has_zero_worker_calls(
    configuration_change, expected, stage
):
    request, service, worker, _, _ = build_canary(stage)
    configuration = replace(request.configuration, **configuration_change)
    result = service.run(replace(request, configuration=configuration))
    assert result.outcome is expected
    assert worker.calls == 0
    assert result.worker_invocations == 0


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_replay_stops_before_second_worker(stage):
    request, service, worker, _, _ = build_canary(stage)
    first = service.run(request)
    second = service.run(request)
    assert first.outcome is PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED
    assert second.outcome in {
        PaperControlledRuntimeCanaryOutcome.CANARY_ALREADY_ADVANCED,
        PaperControlledRuntimeCanaryOutcome.CANARY_DRY_RUN_NOT_READY,
    }
    assert worker.calls == 1
    assert second.worker_invocations == 0


@pytest.mark.parametrize(
    "argv",
    (
        (),
        ("--single-cycle-canary",),
        ("--config", "missing.json"),
        ("--request", "missing.json"),
        ("--config", "missing.json", "--request", "missing.json"),
    ),
)
def test_cli_requires_all_three_explicit_inputs(argv, capsys):
    assert main(list(argv)) == 2
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["outcome"].startswith("CANARY_")


def test_contract_exposes_exact_task_and_migration_identity():
    assert TASK_ID.endswith("SINGLE_CYCLE_CANARY_01_RETRY_02")
    assert EXPECTED_MIGRATION_HEAD == "0013_paper_first_canary_correlation"
    assert CANARY_ACKNOWLEDGEMENT == "I_ACKNOWLEDGE_ONE_ISOLATED_PAPER_STAGE"


def test_request_contains_no_uri_password_or_secret_fields():
    names = {item.name.lower() for item in fields(PaperControlledRuntimeSingleCycleCanaryRequest)}
    assert not names & {"password", "uri", "database_url", "secret", "token"}
