from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import delete, func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAction,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
)
from app.engine_paper.controlled_runtime_canary import (
    EXPECTED_MIGRATION_HEAD,
    TASK_ID as SINGLE_CYCLE_TASK_ID,
    PaperControlledRuntimeCanaryStage,
    PaperControlledRuntimeCanaryTargetIdentity,
    canary_ownership_marker,
)
from app.engine_paper.controlled_runtime_sequence_canary import (
    PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_ARMING_VERSION,
    PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_CONTRACT_VERSION,
    SEQUENCE_ACKNOWLEDGEMENT,
    TASK_ID,
    PaperControlledRuntimeBoundedSequenceArming,
    PaperControlledRuntimeBoundedSequenceCanaryRequest,
    PaperControlledRuntimeBoundedSequenceCanaryService,
    PaperControlledRuntimeBoundedSequenceOutcome,
    PaperControlledRuntimeBoundedSequencePlan,
    PaperControlledRuntimeBoundedSequenceStepPlan,
    PaperControlledRuntimeSequenceFaultPoint,
    PaperControlledRuntimeSequenceMutationBudget,
    aggregate_sequence_budget,
)
from app.engine_paper.controlled_worker import (
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleScope,
    PaperLifecycleState,
)
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import ExecutionMode, PaperPositionState
from tests.paper_controlled_runtime_canary.conftest import NOW
from tests.paper_controlled_runtime_canary.test_postgres_canary import (
    _entry_cycle,
    _ingest_cycle,
    _no_trigger_cycle,
    _prepare,
    _service,
    _trigger_and_close_cycles,
)
from tests.paper_controlled_worker_retry.test_postgres_full_lifecycle import (
    _seed_policy,
)
from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


STAGES = (
    PaperControlledRuntimeCanaryStage.INGEST_COMMAND,
    PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY,
    PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER,
    PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER,
    PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE,
)
STATES_BEFORE = (
    PaperLifecycleState.APPROVALS_ONLY,
    PaperLifecycleState.ENTRY_ORDER_OPEN,
    PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
    PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
    PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN,
)
STATES_AFTER = (
    PaperLifecycleState.ENTRY_ORDER_OPEN,
    PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
    PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
    PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN,
    PaperLifecycleState.POSITION_CLOSED,
)
BUSINESS_MODELS = (
    PaperJournalEntryRecord,
    PaperExitEvaluationCursorRecord,
    PaperExitDecisionRecord,
    PaperPositionRecord,
    PaperFillRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperExecutionCommandRecord,
    PaperSimulationPolicyRecord,
)


def _worker(factory):
    return PaperControlledLifecycleWorker.from_factories(
        lambda: PaperUnitOfWork(factory), factory
    )


def _reset(factory):
    with factory.begin() as session:
        for model in BUSINESS_MODELS:
            session.execute(delete(model))


def _all_cycles(factory, suffix):
    ingestion, correlation = _prepare(factory, suffix)
    worker = _worker(factory)
    ingest = _ingest_cycle(ingestion, correlation, f"{suffix}-ingest")
    worker.run_cycle(ingest)
    entry = _entry_cycle(factory, ingestion, correlation, f"{suffix}-entry")
    worker.run_cycle(entry)
    no_trigger = _no_trigger_cycle(
        factory, ingestion, correlation, f"{suffix}-no-trigger"
    )
    worker.run_cycle(no_trigger)
    trigger, close = _trigger_and_close_cycles(
        factory, ingestion, correlation, suffix
    )
    cycles = (ingest, entry, no_trigger, trigger, close)
    _reset(factory)
    _seed_policy(factory, ingestion)
    return ingestion, cycles


def _seed_prefix(factory, cycles, count):
    worker = _worker(factory)
    for cycle in cycles[:count]:
        result = worker.run_cycle(cycle)
        assert result.stages_completed == 1


def _request(factory, cycles, *, start=0, stop=5, suffix="sequence"):
    selected = cycles[start:stop]
    steps = tuple(
        PaperControlledRuntimeBoundedSequenceStepPlan(
            step_index=index,
            step_id=f"{suffix}:step:{index}",
            expected_initial_state=STATES_BEFORE[source_index],
            expected_stage=STAGES[source_index],
            expected_terminal_or_next_state_class=STATES_AFTER[source_index],
            supplied_input_reference=f"{suffix}:input:{index}",
            mutation_budget=(
                PaperControlledRuntimeSequenceMutationBudget.exact_for_stage(
                    STAGES[source_index]
                )
            ),
            authorization_expires_at=NOW + timedelta(hours=1),
            stop_after_step=index == len(selected) - 1,
        )
        for index, source_index in enumerate(range(start, stop))
    )
    run_id = f"bounded-sequence:{suffix}"
    target = PaperControlledRuntimeCanaryTargetIdentity(
        target_kind=PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
        task_id=SINGLE_CYCLE_TASK_ID,
        canary_run_id=run_id,
        database_name="paper_test_single_cycle_canary_01",
        database_role_name="paper_canary_01_role",
        migration_head=EXPECTED_MIGRATION_HEAD,
        ownership_marker=canary_ownership_marker(
            SINGLE_CYCLE_TASK_ID,
            run_id,
            "paper_test_single_cycle_canary_01",
            "paper_canary_01_role",
        ),
        created_at=NOW,
        expires_at=NOW + timedelta(hours=2),
    )
    configuration = PaperControlledRuntimeConfiguration(
        runtime_action=PaperControlledRuntimeAction.BOUNDED_SEQUENCE_CANARY,
        target=PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
        execution_mode=ExecutionMode.PAPER,
        runtime_enabled=True,
        dry_run_enabled=True,
        explicit_paper_authorization=True,
        explicit_sequence_authorization=True,
        cycle_scope=PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP,
        max_stages_per_cycle=1,
        allowed_symbols=("BTCUSDT",),
        database_access_mode=PaperDatabaseAccessMode.ISOLATED_CANARY_READ_WRITE,
        created_at=NOW,
        configuration_id=f"bounded-sequence:configuration:{suffix}",
    )
    plan = PaperControlledRuntimeBoundedSequencePlan(
        PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_CONTRACT_VERSION,
        TASK_ID,
        run_id,
        configuration.configuration_id,
        target,
        "BTCUSDT",
        ExecutionMode.PAPER,
        steps,
        len(steps),
        NOW,
        NOW + timedelta(hours=1),
        True,
        SEQUENCE_ACKNOWLEDGEMENT,
        aggregate_sequence_budget(steps),
        selected[0].correlation_id,
    )
    arming = PaperControlledRuntimeBoundedSequenceArming(
        PAPER_CONTROLLED_RUNTIME_BOUNDED_SEQUENCE_ARMING_VERSION,
        TASK_ID,
        run_id,
        configuration.configuration_id,
        target,
        "BTCUSDT",
        tuple(step.expected_stage for step in steps),
        len(steps),
        plan.aggregate_mutation_budget,
        NOW + timedelta(minutes=30),
        True,
        SEQUENCE_ACKNOWLEDGEMENT,
    )
    single, graph_loader = _service(factory)
    service = PaperControlledRuntimeBoundedSequenceCanaryService(
        graph_loader=graph_loader,
        single_cycle_canary=single,
    )
    return service, PaperControlledRuntimeBoundedSequenceCanaryRequest(
        request_id=f"request:{run_id}",
        plan=plan,
        arming=arming,
        configuration=configuration,
        ordered_cycle_requests=selected,
        evaluated_at=NOW,
    )


@pytest.mark.parametrize("length", (1, 2, 3, 4, 5))
def test_postgres_prefixes_stop_at_explicit_final_step(
    clean_paper_factory, length
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"prefix-{length}")
    service, request = _request(
        factory, cycles, stop=length, suffix=f"prefix-{length}"
    )
    result = service.run(request)
    assert (
        result.overall_outcome
        is PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED
    )
    assert result.requested_step_count == length
    assert result.completed_step_count == length
    assert result.total_worker_calls == length
    assert result.total_mutating_stages == length
    assert len(result.ordered_step_results) == length
    assert result.final_persisted_state is STATES_AFTER[length - 1]


@pytest.mark.parametrize(
    "start,stop",
    (
        (1, 2),
        (3, 5),
        (2, 4),
        (1, 5),
    ),
)
def test_postgres_targeted_subsequences(clean_paper_factory, start, stop):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"target-{start}-{stop}")
    _seed_prefix(factory, cycles, start)
    service, request = _request(
        factory,
        cycles,
        start=start,
        stop=stop,
        suffix=f"target-{start}-{stop}",
    )
    result = service.run(request)
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED
    )
    assert result.completed_step_count == stop - start
    assert result.total_worker_calls == stop - start
    assert result.final_persisted_state is STATES_AFTER[stop - 1]


def test_postgres_full_five_step_sequence_exact_graph(clean_paper_factory):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "full-five")
    service, request = _request(factory, cycles, suffix="full-five")
    result = service.run(request)
    assert (
        result.overall_outcome
        is PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED
    )
    assert result.completed_step_count == 5
    assert result.total_worker_calls == 5
    assert result.total_mutating_stages == 5
    assert result.aggregate_budget_result == "PASS"
    assert result.final_persisted_state is PaperLifecycleState.POSITION_CLOSED
    with factory() as session:
        counts = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                PaperExecutionCommandRecord,
                PaperOrderRecord,
                PaperFillRecord,
                PaperPositionRecord,
                PaperExitEvaluationCursorRecord,
                PaperExitDecisionRecord,
                PaperOrderEventRecord,
                PaperJournalEntryRecord,
            )
        )
        position = session.scalar(select(PaperPositionRecord))
    assert counts == (1, 2, 2, 1, 1, 1, 8, 12)
    assert position is not None
    assert position.state == PaperPositionState.CLOSED.value
    assert position.realized_pnl is not None


def test_postgres_completed_replay_has_zero_worker_calls(clean_paper_factory):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "replay")
    service, request = _request(factory, cycles, suffix="replay")
    assert service.run(request).completed_step_count == 5
    replay = service.run(request)
    assert replay.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED
    )
    assert replay.total_worker_calls == 0
    assert replay.total_mutating_stages == 0
    assert replay.durable_completed_prefix == 5


@pytest.mark.parametrize("prefix", (1, 2, 3, 4))
def test_postgres_partial_resume_skips_durable_prefix(
    clean_paper_factory, prefix
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"resume-{prefix}")
    _seed_prefix(factory, cycles, prefix)
    service, request = _request(
        factory, cycles, suffix=f"resume-{prefix}"
    )
    result = service.run(request)
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED
    )
    assert result.skipped_step_count == prefix
    assert result.durable_completed_prefix == 5
    assert result.total_worker_calls == 5 - prefix
    assert result.next_resumable_step_index is None


def test_postgres_concurrent_identical_sequences_one_material_graph(
    clean_paper_factory,
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "concurrent")
    service, request = _request(factory, cycles, suffix="concurrent")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _: service.run(request), range(2)))
    assert sorted(result.total_worker_calls for result in results) == [0, 5]
    assert {
        result.overall_outcome for result in results
    } == {
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED,
    }
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 2
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1


class _Cancellation:
    cancelled = False

    def is_cancelled(self):
        return self.cancelled


class _CancelAfterSingle:
    def __init__(self, delegate, cancellation):
        self.delegate = delegate
        self.cancellation = cancellation

    def run(self, request):
        result = self.delegate.run(request)
        self.cancellation.cancelled = True
        return result


def test_postgres_cancellation_preserves_one_step_durable_prefix(
    clean_paper_factory,
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "cancel-prefix")
    service, request = _request(factory, cycles, suffix="cancel-prefix")
    cancellation = _Cancellation()
    service = PaperControlledRuntimeBoundedSequenceCanaryService(
        graph_loader=service._graph_loader,
        single_cycle_canary=_CancelAfterSingle(
            service._single_cycle_canary, cancellation
        ),
    )
    result = service.run(
        replace(request, cancellation_authority=cancellation)
    )
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX
    )
    assert result.durable_completed_prefix == 1
    assert result.total_worker_calls == 1


def test_postgres_cancellation_before_first_mutation_is_zero(
    clean_paper_factory,
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "cancel-before")
    service, request = _request(factory, cycles, suffix="cancel-before")
    cancellation = _Cancellation()
    cancellation.cancelled = True
    result = service.run(
        replace(request, cancellation_authority=cancellation)
    )
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_BEFORE_FIRST_MUTATION
    )
    assert result.total_worker_calls == 0
    assert result.durable_completed_prefix == 0


@pytest.mark.parametrize("durable_prefix", (1, 2, 3, 4, 5))
def test_postgres_fault_after_step_preserves_exact_prefix_and_resumes(
    clean_paper_factory, durable_prefix
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"fault-prefix-{durable_prefix}")
    service, request = _request(
        factory, cycles, suffix=f"fault-prefix-{durable_prefix}"
    )
    seen = 0

    def fault(point):
        nonlocal seen
        if point is PaperControlledRuntimeSequenceFaultPoint.AFTER_SINGLE_CYCLE_CALL:
            seen += 1
            if seen == durable_prefix:
                raise RuntimeError("injected after durable step")

    faulting = PaperControlledRuntimeBoundedSequenceCanaryService(
        graph_loader=service._graph_loader,
        single_cycle_canary=service._single_cycle_canary,
        fault_injector=fault,
    )
    failed = faulting.run(request)
    assert failed.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_FAULT_WITH_DURABLE_PREFIX
    )
    assert failed.durable_completed_prefix == durable_prefix
    assert failed.total_worker_calls == durable_prefix
    resumed = service.run(request)
    assert resumed.total_worker_calls == 5 - durable_prefix
    assert resumed.durable_completed_prefix == 5
    assert resumed.overall_outcome in {
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED,
    }


def test_postgres_ambiguous_resume_fails_before_worker(clean_paper_factory):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "ambiguous")
    _seed_prefix(factory, cycles, 2)
    service, request = _request(factory, cycles, suffix="ambiguous")
    corrupted_entry = replace(cycles[1], entry_fill_id="fill:ambiguous:missing")
    corrupted = replace(
        request,
        ordered_cycle_requests=(
            cycles[0],
            corrupted_entry,
            *cycles[2:],
        ),
    )
    result = service.run(corrupted)
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_RESUME_STATE_AMBIGUOUS
    )
    assert result.total_worker_calls == 0


def test_invalid_sequence_configuration_fails_before_worker(clean_paper_factory):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "invalid-config")
    service, request = _request(
        factory, cycles, stop=1, suffix="invalid-config"
    )
    invalid = replace(
        request,
        configuration=replace(
            request.configuration,
            explicit_sequence_authorization=False,
        ),
    )
    result = service.run(invalid)
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CONFIGURATION_INVALID
    )
    assert result.total_worker_calls == 0


def test_reordered_sequence_arming_fails_before_worker(clean_paper_factory):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "reordered-arming")
    service, request = _request(
        factory, cycles, stop=2, suffix="reordered-arming"
    )
    invalid = replace(
        request,
        arming=replace(
            request.arming,
            ordered_stage_list=tuple(reversed(request.arming.ordered_stage_list)),
        ),
    )
    result = service.run(invalid)
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_AUTHORIZATION_INVALID
    )
    assert result.total_worker_calls == 0


def test_impossible_order_and_aggregate_budget_fail_before_worker(
    clean_paper_factory,
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "invalid-plan")
    service, request = _request(
        factory, cycles, stop=2, suffix="invalid-plan"
    )
    second = replace(
        request.plan.ordered_step_plans[1],
        expected_initial_state=PaperLifecycleState.APPROVALS_ONLY,
    )
    plan = replace(
        request.plan,
        ordered_step_plans=(request.plan.ordered_step_plans[0], second),
        aggregate_mutation_budget=PaperControlledRuntimeSequenceMutationBudget(),
    )
    invalid = replace(request, plan=plan)
    result = service.run(invalid)
    assert result.overall_outcome is (
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PLAN_INVALID
    )
    assert result.total_worker_calls == 0


@pytest.mark.parametrize(
    "point",
    tuple(PaperControlledRuntimeSequenceFaultPoint),
)
def test_fault_injection_is_bounded_and_never_retries(clean_paper_factory, point):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"fault-{point.value.lower()}")
    service, request = _request(
        factory, cycles, stop=1, suffix=f"fault-{point.value.lower()}"
    )

    def fault(candidate):
        if candidate is point:
            raise RuntimeError("injected")

    service = PaperControlledRuntimeBoundedSequenceCanaryService(
        graph_loader=service._graph_loader,
        single_cycle_canary=service._single_cycle_canary,
        fault_injector=fault,
    )
    result = service.run(request)
    assert result.total_worker_calls <= 1
    assert result.total_mutating_stages <= 1
    assert result.failed_step_count <= 1
