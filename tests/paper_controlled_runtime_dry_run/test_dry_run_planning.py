from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_paper.controlled_runtime import (
    PAPER_CONTROLLED_RUNTIME_DRY_RUN_CONTRACT_VERSION,
    PaperControlledRuntimeAction,
    PaperControlledRuntimeAvailableInputSummary,
    PaperControlledRuntimeDryRunService,
    PaperControlledRuntimeOutcome,
    PaperControlledRuntimeTarget,
    PaperDryRunPlanReadiness,
)
from app.engine_paper.controlled_worker import (
    PaperLifecycleCycleScope,
    PaperLifecycleStage,
    PaperLifecycleState,
)
from tests.paper_controlled_runtime_dry_run.conftest import StaticGraphLoader


STATE_CASES = (
    ("empty", PaperLifecycleState.APPROVALS_ONLY, PaperLifecycleStage.INGEST_COMMAND, "approval_input_available", PaperControlledRuntimeOutcome.MISSING_APPROVAL_INPUT),
    ("entry_open", PaperLifecycleState.ENTRY_ORDER_OPEN, PaperLifecycleStage.EXECUTE_ENTRY, "entry_input_available", PaperControlledRuntimeOutcome.MISSING_ENTRY_INPUT),
    ("position_open", PaperLifecycleState.POSITION_OPEN_CURSOR_READY, PaperLifecycleStage.EVALUATE_EXIT, "exit_window_available", PaperControlledRuntimeOutcome.MISSING_EXIT_WINDOW),
    ("position_closing", PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN, PaperLifecycleStage.EXECUTE_CLOSE, "close_input_available", PaperControlledRuntimeOutcome.MISSING_CLOSE_INPUT),
)


@pytest.mark.parametrize(
    ("graph_name", "state", "stage", "input_field", "missing_outcome"), STATE_CASES
)
@pytest.mark.parametrize("available", (False, True))
def test_each_actionable_state_maps_to_one_exact_read_only_plan(
    lifecycle_graphs,
    make_request,
    graph_name,
    state,
    stage,
    input_field,
    missing_outcome,
    available,
):
    loader = StaticGraphLoader(getattr(lifecycle_graphs, graph_name))
    summary = PaperControlledRuntimeAvailableInputSummary(**{input_field: available})
    result = PaperControlledRuntimeDryRunService(loader).plan(
        make_request(available_inputs=summary)
    )
    assert result.initial_lifecycle_state is state
    assert result.next_eligible_stage is stage
    assert len(result.stage_plan) == 1
    assert result.stage_plan[0].stage is stage
    assert result.stage_plan[0].would_mutate_in_real_cycle is True
    assert result.business_mutation_count == 0
    assert result.commit_count == 0
    assert result.child_mutation_call_count == 0
    if available:
        assert result.dry_run_status is PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY
        assert result.stage_plan[0].readiness is PaperDryRunPlanReadiness.READY
    else:
        assert result.dry_run_status is PaperControlledRuntimeOutcome.DRY_RUN_BLOCKED_AWAITING_INPUT
        assert result.missing_inputs == (missing_outcome.value,)


def test_closed_state_returns_complete_without_stage(lifecycle_graphs, make_request):
    result = PaperControlledRuntimeDryRunService(
        StaticGraphLoader(lifecycle_graphs.position_closed)
    ).plan(make_request())
    assert result.initial_lifecycle_state is PaperLifecycleState.POSITION_CLOSED
    assert result.dry_run_status is PaperControlledRuntimeOutcome.DRY_RUN_COMPLETE
    assert result.next_eligible_stage is None
    assert result.stage_plan == ()


def test_inconsistent_state_fails_closed(lifecycle_graphs, make_request):
    result = PaperControlledRuntimeDryRunService(
        StaticGraphLoader(replace(lifecycle_graphs.position_open, bounded_limit_reached=True))
    ).plan(make_request())
    assert result.dry_run_status is PaperControlledRuntimeOutcome.SOURCE_GRAPH_INCONSISTENT
    assert result.stage_plan == ()


@pytest.mark.parametrize("max_stages", (2, 3, 4))
@pytest.mark.parametrize("graph_name", ("empty", "entry_open", "position_open"))
def test_multistage_plan_is_bounded_and_future_items_are_only_conditional(
    lifecycle_graphs, make_request, paper_configuration, max_stages, graph_name
):
    configuration = replace(
        paper_configuration,
        cycle_scope=PaperLifecycleCycleScope.ADVANCE_UNTIL_BLOCKED_WITHIN_REQUEST,
        max_stages_per_cycle=max_stages,
    )
    all_inputs = PaperControlledRuntimeAvailableInputSummary(True, True, True, True, True)
    result = PaperControlledRuntimeDryRunService(
        StaticGraphLoader(getattr(lifecycle_graphs, graph_name))
    ).plan(make_request(configuration=configuration, available_inputs=all_inputs))
    assert 1 <= len(result.stage_plan) <= max_stages <= 4
    assert result.stage_plan[0].readiness is PaperDryRunPlanReadiness.READY
    assert all(
        item.readiness is PaperDryRunPlanReadiness.CONDITIONAL
        and item.blocking_reason == "FOLLOWING_STAGE_REQUIRES_FUTURE_PERSISTED_PRECONDITION"
        for item in result.stage_plan[1:]
    )


@pytest.mark.parametrize(
    "selector",
    (
        {"entry_order_id": "order:missing"},
        {"position_id": "position:missing"},
        {"cursor_id": "cursor:missing"},
        {"expected_command_version": 0},
        {"expected_position_version": 0},
    ),
)
def test_empty_graph_with_existing_identity_expectation_is_not_approvals_only(
    lifecycle_graphs, make_request, selector
):
    result = PaperControlledRuntimeDryRunService(
        StaticGraphLoader(lifecycle_graphs.empty)
    ).plan(make_request(**selector))
    assert result.dry_run_status is PaperControlledRuntimeOutcome.GRAPH_NOT_FOUND


@pytest.mark.parametrize(
    "expected_field",
    (
        "expected_command_version",
        "expected_entry_order_version",
        "expected_position_version",
        "expected_cursor_version",
        "expected_close_order_version",
    ),
)
def test_stale_expected_versions_fail_before_planning(
    lifecycle_graphs, make_request, expected_field
):
    result = PaperControlledRuntimeDryRunService(
        StaticGraphLoader(lifecycle_graphs.position_closing)
    ).plan(make_request(**{expected_field: 999}))
    assert result.dry_run_status is PaperControlledRuntimeOutcome.STALE_EXPECTED_VERSION
    assert result.stage_plan == ()


def test_symbol_must_belong_to_immutable_allowlist(lifecycle_graphs, make_request):
    loader = StaticGraphLoader(lifecycle_graphs.empty)
    result = PaperControlledRuntimeDryRunService(loader).plan(
        make_request(symbol="ETHUSDT")
    )
    assert result.dry_run_status is PaperControlledRuntimeOutcome.SYMBOL_NOT_ALLOWED
    assert loader.calls == 0


@pytest.mark.parametrize(
    "target",
    (
        PaperControlledRuntimeTarget.CONFIGURATION_ONLY,
        PaperControlledRuntimeTarget.PRODUCTION_READONLY_METADATA,
    ),
)
def test_non_isolated_targets_are_configuration_only_and_never_load_graph(
    lifecycle_graphs, make_request, paper_configuration, target
):
    loader = StaticGraphLoader(lifecycle_graphs.position_open)
    configuration = replace(
        paper_configuration,
        target=target,
        database_access_mode="NONE",
    )
    result = PaperControlledRuntimeDryRunService(loader).plan(
        make_request(configuration=configuration)
    )
    assert result.dry_run_status is PaperControlledRuntimeOutcome.DRY_RUN_CONFIGURATION_ONLY
    assert loader.calls == 0
    assert result.initial_lifecycle_state is None


class Cancellation:
    def __init__(self, answers):
        self.answers = iter(answers)

    def is_cancelled(self):
        return next(self.answers)


def test_cancellation_before_read(lifecycle_graphs, make_request):
    loader = StaticGraphLoader(lifecycle_graphs.position_open)
    result = PaperControlledRuntimeDryRunService(loader).plan(
        make_request(cancellation_authority=Cancellation([True]))
    )
    assert result.dry_run_status is PaperControlledRuntimeOutcome.CANCELLED
    assert loader.calls == 0


def test_cancellation_after_read(lifecycle_graphs, make_request):
    loader = StaticGraphLoader(lifecycle_graphs.position_open)
    result = PaperControlledRuntimeDryRunService(loader).plan(
        make_request(cancellation_authority=Cancellation([False, True]))
    )
    assert result.dry_run_status is PaperControlledRuntimeOutcome.CANCELLED_AFTER_READ
    assert loader.calls == 1


@pytest.mark.parametrize("repeat", tuple(range(24)))
def test_same_request_and_graph_produce_identical_result(
    lifecycle_graphs, make_request, repeat
):
    request = make_request(
        available_inputs=PaperControlledRuntimeAvailableInputSummary(
            exit_window_available=True
        )
    )
    service = PaperControlledRuntimeDryRunService(
        StaticGraphLoader(lifecycle_graphs.position_open)
    )
    assert service.plan(request) == service.plan(request)


def test_unsupported_dry_run_contract_fails_without_graph_access(
    lifecycle_graphs, make_request
):
    loader = StaticGraphLoader(lifecycle_graphs.position_open)
    result = PaperControlledRuntimeDryRunService(loader).plan(
        make_request(contract_version="PAPER_CONTROLLED_RUNTIME_DRY_RUN_V999")
    )
    assert result.dry_run_status is PaperControlledRuntimeOutcome.INVALID_DRY_RUN_REQUEST
    assert loader.calls == 0
