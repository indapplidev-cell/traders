from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import delete, event, inspect, select, text

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
from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAvailableInputSummary,
    PaperControlledRuntimeDryRunService,
    PaperControlledRuntimeOutcome,
    SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader,
)
from app.engine_paper.controlled_worker import PaperLifecycleState
from app.engine_paper.repositories import PaperRepositories
from tests.paper_command_ingestion_retry.conftest import make_request as make_ingestion_request
from tests.paper_controlled_worker_retry.test_postgres_full_lifecycle import (
    _at,
    _candle,
    _cycle,
    _entry_request,
    _exit_request,
    _seed_policy,
    _worker,
)
from app.engine_execution.paper_idempotency import simulated_close_fill_id
from app.engine_paper.fill_causal_boundary import PAPER_FILL_CAUSAL_BOUNDARY_VERSION
from app.engine_paper.fill_simulator import PaperFillRole
from app.engine_paper.order_execution_service import PaperCloseExecutionRequest


MODELS = (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    PaperFillRecord,
    PaperPositionRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperOrderEventRecord,
    PaperJournalEntryRecord,
)


def _counts(factory):
    with factory() as session:
        return tuple(session.scalar(select(text("count(*)")).select_from(model)) for model in MODELS)


def _snapshot(factory):
    with factory() as session:
        snapshot = []
        for model in MODELS:
            mapper = inspect(model)
            columns = tuple(column.key for column in mapper.columns)
            primary_key = tuple(column.key for column in mapper.primary_key)
            rows = tuple(
                tuple(getattr(row, name) for name in columns)
                for row in session.scalars(
                    select(model).order_by(*(getattr(model, name) for name in primary_key))
                )
            )
            snapshot.append((model.__tablename__, columns, rows))
        return tuple(snapshot)


def _assert_read_only_plan(service, request, expected_state, expected_outcome, factory):
    before = _snapshot(factory)
    result = service.plan(request)
    after = _snapshot(factory)
    assert result.initial_lifecycle_state is expected_state
    assert result.dry_run_status is expected_outcome
    assert before == after
    assert result.business_mutation_count == 0
    assert result.commit_count == 0
    assert result.child_mutation_call_count == 0
    return result


def test_postgres_loader_uses_read_only_transaction_and_rolls_back(
    paper_session_factory, lifecycle_graphs
):
    loader = SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader(paper_session_factory)
    graph = loader.load(lifecycle_graphs.empty.command_id)
    assert graph.command is None
    assert loader.last_database_read_only_transaction is True


def test_postgres_read_only_transaction_rejects_mutation(paper_session_factory):
    session = paper_session_factory()
    transaction = session.begin()
    try:
        session.execute(text("SET TRANSACTION READ ONLY"))
        with pytest.raises(Exception):
            session.execute(text("CREATE TEMP TABLE forbidden_runtime_write(id integer)"))
    finally:
        if transaction.is_active:
            transaction.rollback()
        session.close()


def test_postgres_dry_run_empty_graph_has_zero_sql_mutations(
    paper_session_factory, make_request
):
    statements = Counter()

    def spy(conn, cursor, statement, parameters, context, executemany):
        verb = statement.lstrip().split(None, 1)[0].upper()
        statements[verb] += 1

    engine = paper_session_factory.kw["bind"]
    before = _counts(paper_session_factory)
    event.listen(engine, "before_cursor_execute", spy)
    try:
        service = PaperControlledRuntimeDryRunService(
            SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader(paper_session_factory)
        )
        result = service.plan(
            make_request(
                available_inputs=PaperControlledRuntimeAvailableInputSummary(
                    approval_input_available=True
                )
            )
        )
    finally:
        event.remove(engine, "before_cursor_execute", spy)
    after = _counts(paper_session_factory)
    assert result.dry_run_status is PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY
    assert result.initial_lifecycle_state is PaperLifecycleState.APPROVALS_ONLY
    assert before == after
    assert statements["INSERT"] == statements["UPDATE"] == statements["DELETE"] == 0
    assert result.read_only_proof.database_read_only_transaction is True
    assert result.business_mutation_count == result.commit_count == result.child_mutation_call_count == 0


def test_postgres_all_six_states_are_planned_with_exact_before_after_equality(
    paper_session_factory, make_request
):
    factory = paper_session_factory
    worker = _worker(factory)
    ingestion = make_ingestion_request(identity_suffix="runtime-dry-run-six-states")
    _seed_policy(factory, ingestion)
    service = PaperControlledRuntimeDryRunService(
        SqlAlchemyPaperControlledRuntimeReadOnlyGraphLoader(factory)
    )

    _assert_read_only_plan(
        service,
        make_request(
            command_id=ingestion.command_id,
            symbol=ingestion.paper_strategy_approval.symbol,
            available_inputs=PaperControlledRuntimeAvailableInputSummary(
                approval_input_available=True
            ),
        ),
        PaperLifecycleState.APPROVALS_ONLY,
        PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY,
        factory,
    )

    worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "runtime-dry-ingest",
            correlation_id=ingestion.correlation_id,
            entry_order_id=ingestion.order_id,
            ingestion_request=ingestion,
        )
    )
    _assert_read_only_plan(
        service,
        make_request(
            command_id=ingestion.command_id,
            symbol=ingestion.paper_strategy_approval.symbol,
            available_inputs=PaperControlledRuntimeAvailableInputSummary(
                entry_input_available=True
            ),
        ),
        PaperLifecycleState.ENTRY_ORDER_OPEN,
        PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY,
        factory,
    )

    from tests.paper_controlled_worker_retry.test_postgres_full_lifecycle import _load

    graph = _load(factory, ingestion.command_id)
    entry_request = _entry_request(
        graph, ingestion.simulation_policy, ingestion.correlation_id
    )
    worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "runtime-dry-entry",
            correlation_id=ingestion.correlation_id,
            entry_order_id=entry_request.order_id,
            entry_fill_id=entry_request.fill_id,
            position_id=entry_request.position_id,
            entry_execution_request=entry_request,
        )
    )
    _assert_read_only_plan(
        service,
        make_request(
            command_id=ingestion.command_id,
            symbol=ingestion.paper_strategy_approval.symbol,
            available_inputs=PaperControlledRuntimeAvailableInputSummary(
                exit_window_available=True
            ),
        ),
        PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
        PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY,
        factory,
    )

    graph = _load(factory, ingestion.command_id)
    trigger_boundary = graph.cursors[0].last_evaluated_closed_until_ms + 60_000
    exit_decision_id = "exit:postgres:runtime-dry-trigger"
    close_order_id = "order:postgres:close:runtime-dry-trigger"
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
        suffix="runtime-dry-trigger",
        trigger=True,
        close_fill_id=close_fill_id,
        correlation_id=ingestion.correlation_id,
    )
    worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "runtime-dry-trigger",
            correlation_id=ingestion.correlation_id,
            position_id=graph.positions[0].position_id,
            cursor_id=graph.cursors[0].cursor_id,
            exit_decision_id=exit_decision_id,
            close_order_id=close_order_id,
            exit_evaluation_request=trigger_request,
        )
    )
    _assert_read_only_plan(
        service,
        make_request(
            command_id=ingestion.command_id,
            symbol=ingestion.paper_strategy_approval.symbol,
            available_inputs=PaperControlledRuntimeAvailableInputSummary(
                close_input_available=True
            ),
        ),
        PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN,
        PaperControlledRuntimeOutcome.DRY_RUN_NEXT_STAGE_READY,
        factory,
    )

    graph = _load(factory, ingestion.command_id)
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
        expected_position_version=graph.positions[0].version,
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
        correlation_id=ingestion.correlation_id,
        causation_id=trigger_request.causation_id,
        operation_at=_at(close_candle.close_boundary_ms),
    )
    worker.run_cycle(
        _cycle(
            ingestion.command_id,
            "runtime-dry-close",
            correlation_id=ingestion.correlation_id,
            position_id=close_request.position_id,
            exit_decision_id=close_request.exit_decision_id,
            close_order_id=close_request.order_id,
            close_fill_id=close_request.fill_id,
            close_execution_request=close_request,
        )
    )
    _assert_read_only_plan(
        service,
        make_request(
            command_id=ingestion.command_id,
            symbol=ingestion.paper_strategy_approval.symbol,
        ),
        PaperLifecycleState.POSITION_CLOSED,
        PaperControlledRuntimeOutcome.DRY_RUN_COMPLETE,
        factory,
    )

    with factory.begin() as session:
        session.execute(
            delete(PaperJournalEntryRecord).where(
                PaperJournalEntryRecord.command_id == ingestion.command_id
            )
        )
    _assert_read_only_plan(
        service,
        make_request(
            command_id=ingestion.command_id,
            symbol=ingestion.paper_strategy_approval.symbol,
        ),
        PaperLifecycleState.INCONSISTENT,
        PaperControlledRuntimeOutcome.SOURCE_GRAPH_INCONSISTENT,
        factory,
    )
