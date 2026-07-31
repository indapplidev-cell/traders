from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select, text

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_execution.paper_idempotency import simulated_close_fill_id
from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAction,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeDryRunService,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
    SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader,
)
from app.engine_paper.controlled_runtime_canary import (
    CANARY_ACKNOWLEDGEMENT,
    EXPECTED_MIGRATION_HEAD,
    PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION,
    TASK_ID,
    PaperControlledRuntimeCanaryArming,
    PaperControlledRuntimeCanaryMutationBudget,
    PaperControlledRuntimeCanaryOutcome,
    PaperControlledRuntimeCanaryStage,
    PaperControlledRuntimeCanaryTargetIdentity,
    PaperControlledRuntimeSingleCycleCanaryRequest,
    PaperControlledRuntimeSingleCycleCanaryService,
    SqlAlchemyPaperControlledRuntimeCanaryTargetValidator,
    canary_ownership_marker,
    paper_canary_graph_fingerprint,
)
from app.engine_paper.controlled_worker import (
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleScope,
    PaperLifecycleState,
    SqlAlchemyPaperLifecycleGraphLoader,
    classify_paper_lifecycle_state,
)
from app.engine_paper.fill_causal_boundary import PAPER_FILL_CAUSAL_BOUNDARY_VERSION
from app.engine_paper.fill_simulator import PaperFillRole
from app.engine_paper.order_execution_service import PaperCloseExecutionRequest
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import ExecutionMode, PaperPositionState
from tests.paper_command_ingestion_retry.conftest import make_request as make_ingestion_request
from tests.paper_controlled_runtime_canary.conftest import NOW
from tests.paper_controlled_worker_retry.test_postgres_full_lifecycle import (
    _at,
    _candle,
    _cycle,
    _entry_request,
    _exit_request,
    _load,
    _seed_policy,
    clean_paper_factory,
)
from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


def _service(factory):
    graph_loader = SqlAlchemyPaperLifecycleGraphLoader(
        lambda: PaperUnitOfWork(factory)
    )
    dry_loader = SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader(factory)
    return (
        PaperControlledRuntimeSingleCycleCanaryService(
            graph_loader=graph_loader,
            dry_run_service=PaperControlledRuntimeDryRunService(dry_loader),
            worker=PaperControlledLifecycleWorker.from_factories(
                lambda: PaperUnitOfWork(factory), factory
            ),
            target_validator=SqlAlchemyPaperControlledRuntimeCanaryTargetValidator(
                factory
            ),
        ),
        graph_loader,
    )


def _request(factory, stage, cycle, suffix):
    _, graph_loader = _service(factory)
    graph = graph_loader.load(cycle.command_id)
    configuration = PaperControlledRuntimeConfiguration(
        runtime_action=PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY,
        target=PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
        execution_mode=ExecutionMode.PAPER,
        runtime_enabled=True,
        dry_run_enabled=True,
        explicit_paper_authorization=True,
        cycle_scope=PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP,
        max_stages_per_cycle=1,
        allowed_symbols=("BTCUSDT",),
        database_access_mode=PaperDatabaseAccessMode.ISOLATED_CANARY_READ_WRITE,
        created_at=NOW,
        configuration_id=f"canary:postgres:configuration:{suffix}",
    )
    run_id = f"canary-postgres-{suffix}"
    database_name = "paper_test_single_cycle_canary_01"
    role_name = "paper_canary_01_role"
    identity = PaperControlledRuntimeCanaryTargetIdentity(
        target_kind=PaperControlledRuntimeTarget.ISOLATED_POSTGRESQL,
        task_id=TASK_ID,
        canary_run_id=run_id,
        database_name=database_name,
        database_role_name=role_name,
        migration_head=EXPECTED_MIGRATION_HEAD,
        ownership_marker=canary_ownership_marker(
            TASK_ID, run_id, database_name, role_name
        ),
        created_at=NOW,
        expires_at=NOW + timedelta(hours=1),
    )
    fingerprint = paper_canary_graph_fingerprint(graph, stage)
    arming = PaperControlledRuntimeCanaryArming(
        arming_contract_version=PAPER_CONTROLLED_RUNTIME_CANARY_ARMING_VERSION,
        task_id=TASK_ID,
        canary_run_id=run_id,
        configuration_id=configuration.configuration_id,
        target_identity=identity,
        expected_stage=stage,
        expected_graph_fingerprint=fingerprint,
        expires_at=NOW + timedelta(minutes=30),
        single_use=True,
        explicit_acknowledgement=CANARY_ACKNOWLEDGEMENT,
    )
    return PaperControlledRuntimeSingleCycleCanaryRequest(
        request_id=f"request:{run_id}",
        task_id=TASK_ID,
        canary_run_id=run_id,
        configuration=configuration,
        target_identity=identity,
        arming=arming,
        cycle_request=cycle,
        expected_initial_state=classify_paper_lifecycle_state(graph),
        expected_stage=stage,
        expected_graph_fingerprint=fingerprint,
        expected_mutation_budget=(
            PaperControlledRuntimeCanaryMutationBudget.exact_for_stage(stage)
        ),
        created_at=NOW,
        evaluated_at=NOW,
        correlation_id=cycle.correlation_id,
        symbol="BTCUSDT",
    )


def _run_canary(factory, stage, cycle, suffix):
    service, _ = _service(factory)
    request = _request(factory, stage, cycle, suffix)
    result = service.run(request)
    assert result.outcome is PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED, (
        stage,
        result.outcome,
        result.dry_run_outcome,
        result.worker_outcome,
        result.child_outcome,
        result.row_count_deltas,
    )
    assert result.worker_invocations == 1
    assert result.mutating_stage_invocations == 1
    assert result.mutation_budget_result == "PASS"
    return result, request, service


def _prepare(factory, suffix):
    ingestion = make_ingestion_request(identity_suffix=suffix)
    _seed_policy(factory, ingestion)
    correlation = ingestion.correlation_id
    return ingestion, correlation


def _ingest_cycle(ingestion, correlation, suffix):
    return _cycle(
        ingestion.command_id,
        suffix,
        correlation_id=correlation,
        entry_order_id=ingestion.order_id,
        ingestion_request=ingestion,
    )


def _entry_cycle(factory, ingestion, correlation, suffix):
    graph = _load(factory, ingestion.command_id)
    request = _entry_request(graph, ingestion.simulation_policy, correlation)
    return _cycle(
        ingestion.command_id,
        suffix,
        correlation_id=correlation,
        entry_order_id=request.order_id,
        entry_fill_id=request.fill_id,
        position_id=request.position_id,
        entry_execution_request=request,
    )


def _no_trigger_cycle(factory, ingestion, correlation, suffix):
    graph = _load(factory, ingestion.command_id)
    request = _exit_request(
        graph,
        suffix=suffix,
        trigger=False,
        close_fill_id=f"fill:postgres:unused:{suffix}",
        correlation_id=correlation,
    )
    return _cycle(
        ingestion.command_id,
        suffix,
        correlation_id=correlation,
        position_id=graph.positions[0].position_id,
        cursor_id=graph.cursors[0].cursor_id,
        exit_evaluation_request=request,
    )


def _trigger_and_close_cycles(factory, ingestion, correlation, suffix):
    graph = _load(factory, ingestion.command_id)
    trigger_boundary = graph.cursors[0].last_evaluated_closed_until_ms + 60_000
    exit_decision_id = f"exit:postgres:{suffix}"
    close_order_id = f"order:postgres:close:{suffix}"
    close_fill_id = simulated_close_fill_id(
        fill_contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
        order_id=close_order_id,
        exit_decision_id=exit_decision_id,
        exit_source_closed_until_ms=trigger_boundary,
        source_open_time_ms=trigger_boundary,
        source_close_boundary_ms=trigger_boundary + 60_000,
        simulation_policy_id=ingestion.simulation_policy.simulation_policy_id,
        slippage_policy_id=ingestion.simulation_policy.slippage_policy_id,
        fee_policy_id=ingestion.simulation_policy.fee_policy_id,
        latency_policy_id=ingestion.simulation_policy.latency_policy_id,
    )
    trigger_request = _exit_request(
        graph,
        suffix=suffix,
        trigger=True,
        close_fill_id=close_fill_id,
        correlation_id=correlation,
    )
    trigger_cycle = _cycle(
        ingestion.command_id,
        f"{suffix}-trigger",
        correlation_id=correlation,
        position_id=graph.positions[0].position_id,
        cursor_id=graph.cursors[0].cursor_id,
        exit_decision_id=exit_decision_id,
        close_order_id=close_order_id,
        exit_evaluation_request=trigger_request,
    )
    close_candle = _candle(
        symbol=graph.command.symbol,
        open_ms=trigger_boundary,
        open_price=graph.command.stop_price,
        high_price=graph.command.stop_price,
        low_price=graph.command.stop_price,
        close_price=graph.command.stop_price,
    )
    close_request = PaperCloseExecutionRequest(
        command_id=ingestion.command_id,
        order_id=close_order_id,
        expected_order_version=2,
        position_id=graph.positions[0].position_id,
        expected_position_version=graph.positions[0].version + 1,
        exit_decision_id=exit_decision_id,
        fill_role=PaperFillRole.CLOSE,
        candidate_candles=(close_candle,),
        market_snapshot_closed_until_ms=close_candle.close_boundary_ms,
        simulation_policy=ingestion.simulation_policy,
        price_quantum=ingestion.simulation_policy.price_quantum,
        fee_quantum=ingestion.simulation_policy.fee_quantum,
        quote_asset="USDT",
        fill_id=close_fill_id,
        order_event_id=trigger_request.close_execution_order_event_id,
        position_event_id=trigger_request.close_execution_position_event_id,
        journal_entry_ids=trigger_request.close_execution_journal_entry_ids,
        correlation_id=correlation,
        causation_id=trigger_request.causation_id,
        operation_at=_at(close_candle.close_boundary_ms),
    )
    close_cycle = _cycle(
        ingestion.command_id,
        f"{suffix}-close",
        correlation_id=correlation,
        position_id=close_request.position_id,
        exit_decision_id=close_request.exit_decision_id,
        close_order_id=close_request.order_id,
        close_fill_id=close_request.fill_id,
        close_execution_request=close_request,
    )
    return trigger_cycle, close_cycle


def _advance_seed(factory, ingestion, correlation, through):
    worker = PaperControlledLifecycleWorker.from_factories(
        lambda: PaperUnitOfWork(factory), factory
    )
    worker.run_cycle(_ingest_cycle(ingestion, correlation, f"seed-{through}-ingest"))
    if through == "ingest":
        return
    worker.run_cycle(_entry_cycle(factory, ingestion, correlation, f"seed-{through}-entry"))
    if through == "entry":
        return
    worker.run_cycle(
        _no_trigger_cycle(factory, ingestion, correlation, f"seed-{through}-no-trigger")
    )
    if through == "no-trigger":
        return
    trigger, _ = _trigger_and_close_cycles(
        factory, ingestion, correlation, f"seed-{through}"
    )
    worker.run_cycle(trigger)


@pytest.mark.parametrize(
    "stage,seed_through",
    (
        (PaperControlledRuntimeCanaryStage.INGEST_COMMAND, None),
        (PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY, "ingest"),
        (
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER,
            "entry",
        ),
        (
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER,
            "no-trigger",
        ),
        (PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE, "no-trigger"),
    ),
)
def test_isolated_postgres_each_stage_canary(clean_paper_factory, stage, seed_through):
    factory = clean_paper_factory
    suffix = f"matrix-{stage.value.lower().replace('_', '-')}"
    ingestion, correlation = _prepare(factory, suffix)
    if seed_through:
        _advance_seed(factory, ingestion, correlation, seed_through)
    if stage is PaperControlledRuntimeCanaryStage.INGEST_COMMAND:
        cycle = _ingest_cycle(ingestion, correlation, suffix)
    elif stage is PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY:
        cycle = _entry_cycle(factory, ingestion, correlation, suffix)
    elif stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER:
        cycle = _no_trigger_cycle(factory, ingestion, correlation, suffix)
    elif stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER:
        cycle, _ = _trigger_and_close_cycles(factory, ingestion, correlation, suffix)
    else:
        trigger_cycle, cycle = _trigger_and_close_cycles(
            factory, ingestion, correlation, suffix
        )
        PaperControlledLifecycleWorker.from_factories(
            lambda: PaperUnitOfWork(factory), factory
        ).run_cycle(trigger_cycle)
    result, request, service = _run_canary(factory, stage, cycle, suffix)
    replay = service.run(request)
    assert replay.outcome in {
        PaperControlledRuntimeCanaryOutcome.CANARY_ALREADY_ADVANCED,
        PaperControlledRuntimeCanaryOutcome.CANARY_DRY_RUN_NOT_READY,
    }
    assert replay.worker_invocations == 0


def test_sequential_five_explicit_postgres_canary_invocations(clean_paper_factory):
    factory = clean_paper_factory
    ingestion, correlation = _prepare(factory, "sequential")
    invocations = []
    result, _, _ = _run_canary(
        factory,
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND,
        _ingest_cycle(ingestion, correlation, "sequence-ingest"),
        "sequence-ingest",
    )
    invocations.append(result)
    result, _, _ = _run_canary(
        factory,
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY,
        _entry_cycle(factory, ingestion, correlation, "sequence-entry"),
        "sequence-entry",
    )
    invocations.append(result)
    result, _, _ = _run_canary(
        factory,
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER,
        _no_trigger_cycle(factory, ingestion, correlation, "sequence-no-trigger"),
        "sequence-no-trigger",
    )
    invocations.append(result)
    trigger, close = _trigger_and_close_cycles(
        factory, ingestion, correlation, "sequence"
    )
    result, _, _ = _run_canary(
        factory,
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER,
        trigger,
        "sequence-trigger",
    )
    invocations.append(result)
    result, _, _ = _run_canary(
        factory,
        PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE,
        close,
        "sequence-close",
    )
    invocations.append(result)
    assert len(invocations) == 5
    assert sum(item.worker_invocations for item in invocations) == 5
    with factory() as session:
        counts = {
            model.__tablename__: session.scalar(
                select(func.count()).select_from(model)
            )
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
        }
        position = session.scalar(select(PaperPositionRecord))
        revision = session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    assert counts == {
        "paper_execution_commands": 1,
        "paper_orders": 2,
        "paper_fills": 2,
        "paper_positions": 1,
        "paper_exit_evaluation_cursors": 1,
        "paper_exit_decisions": 1,
        "paper_order_events": 8,
        "paper_journal_entries": 12,
    }
    assert position.state == PaperPositionState.CLOSED.value
    assert position.entry_fees > 0
    assert position.exit_fees > 0
    assert revision == EXPECTED_MIGRATION_HEAD
