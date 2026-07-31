from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.engine_paper.controlled_runtime import (
    PaperControlledRuntimeAction,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeDryRunService,
    PaperControlledRuntimeTarget,
    PaperDatabaseAccessMode,
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
    PaperControlledRuntimeCanaryTargetValidation,
    PaperControlledRuntimeSingleCycleCanaryRequest,
    PaperControlledRuntimeSingleCycleCanaryService,
    canary_ownership_marker,
    paper_canary_graph_fingerprint,
)
from app.engine_paper.controlled_worker import (
    PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
    PaperLifecycleCycleOutcome,
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleResult,
    PaperLifecycleCycleScope,
    PaperLifecycleStageTrace,
    PaperLifecycleState,
)
from app.engine_safety import ExecutionMode
from tests.paper_controlled_worker_retry.conftest import build_graphs


NOW = datetime(2026, 7, 31, 8, 0, tzinfo=timezone.utc)


class MutableGraphLoader:
    def __init__(self, graph):
        self.graph = graph
        self.calls = 0
        self.last_database_read_only_transaction = True

    def load(self, command_id):
        self.calls += 1
        assert command_id == self.graph.command_id
        return self.graph


class StaticTargetValidator:
    def validate(self, identity):
        return PaperControlledRuntimeCanaryTargetValidation(
            True,
            PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED,
            identity.migration_head,
            identity.database_name,
            identity.database_role_name,
        )


class AdvancingWorker:
    def __init__(self, loader, after_graph, stage, child_outcome):
        self.loader = loader
        self.after_graph = after_graph
        self.stage = stage
        self.child_outcome = child_outcome
        self.calls = 0

    def run_cycle(self, request):
        self.calls += 1
        before_state = _state_for_stage(self.stage)
        self.loader.graph = self.after_graph
        after_state = {
            PaperControlledRuntimeCanaryStage.INGEST_COMMAND: (
                PaperLifecycleState.ENTRY_ORDER_OPEN
            ),
            PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY: (
                PaperLifecycleState.POSITION_OPEN_CURSOR_READY
            ),
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER: (
                PaperLifecycleState.POSITION_OPEN_CURSOR_READY
            ),
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER: (
                PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN
            ),
            PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE: (
                PaperLifecycleState.POSITION_CLOSED
            ),
        }[self.stage]
        worker_stage = {
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER: "EVALUATE_EXIT",
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER: "EVALUATE_EXIT",
        }.get(self.stage, self.stage.value)
        trace = PaperLifecycleStageTrace(
            stage=__import__(
                "app.engine_paper.controlled_worker", fromlist=["PaperLifecycleStage"]
            ).PaperLifecycleStage(worker_stage),
            state_before=before_state,
            state_after=after_state,
            child_outcome_code=self.child_outcome,
            child_reason_code="TEST_CHILD_OK",
            mutation_committed=True,
        )
        return PaperLifecycleCycleResult(
            cycle_id=request.cycle_id,
            outcome=(
                PaperLifecycleCycleOutcome.CYCLE_COMPLETE
                if self.stage is PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE
                else PaperLifecycleCycleOutcome.CYCLE_STAGE_COMPLETED
            ),
            reason_code="PAPER_LIFECYCLE_OK",
            initial_lifecycle_state=before_state,
            final_lifecycle_state=after_state,
            stages_attempted=1,
            stages_completed=1,
            stage_trace=(trace,),
            child_outcome_codes=(self.child_outcome,),
            child_reason_codes=("TEST_CHILD_OK",),
            command_id=request.command_id,
            entry_order_id=request.entry_order_id,
            entry_fill_id=request.entry_fill_id,
            position_id=request.position_id,
            position_state=(
                self.after_graph.positions[0].state
                if self.after_graph.positions
                else None
            ),
            position_version=(
                self.after_graph.positions[0].version
                if self.after_graph.positions
                else None
            ),
            cursor_id=request.cursor_id,
            cursor_version=(
                self.after_graph.cursors[0].version
                if self.after_graph.cursors
                else None
            ),
            cursor_boundary_ms=(
                self.after_graph.cursors[0].last_evaluated_closed_until_ms
                if self.after_graph.cursors
                else None
            ),
            exit_decision_id=request.exit_decision_id,
            close_order_id=request.close_order_id,
            close_fill_id=request.close_fill_id,
            correlation_id=request.correlation_id,
        )


def _state_for_stage(stage):
    return {
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND: (
            PaperLifecycleState.APPROVALS_ONLY
        ),
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY: (
            PaperLifecycleState.ENTRY_ORDER_OPEN
        ),
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER: (
            PaperLifecycleState.POSITION_OPEN_CURSOR_READY
        ),
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER: (
            PaperLifecycleState.POSITION_OPEN_CURSOR_READY
        ),
        PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE: (
            PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN
        ),
    }[stage]


def _graphs_for_stage(stage):
    graphs = build_graphs()
    if stage is PaperControlledRuntimeCanaryStage.INGEST_COMMAND:
        return (
            __import__(
                "app.engine_paper.controlled_worker", fromlist=["PaperLifecycleGraph"]
            ).PaperLifecycleGraph(command_id=graphs.command.command_id),
            graphs.entry_open,
        )
    if stage is PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY:
        return graphs.entry_open, graphs.position_open
    if stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER:
        cursor = graphs.position_open.cursors[0]
        after = replace(
            graphs.position_open,
            cursors=(
                replace(
                    cursor,
                    version=cursor.version + 1,
                    last_evaluated_closed_until_ms=(
                        cursor.last_evaluated_closed_until_ms + 60_000
                    ),
                ),
            ),
        )
        return graphs.position_open, after
    if stage is PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER:
        return graphs.position_open, graphs.position_closing
    return graphs.position_closing, graphs.position_closed


def _child_outcome(stage):
    return {
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND: (
            "COMMAND_AND_ENTRY_ORDER_CREATED"
        ),
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY: "ENTRY_EXECUTED",
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER: (
            "NO_EXIT_TRIGGER_CURSOR_ADVANCED"
        ),
        PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER: (
            "EXIT_TRIGGERED_AND_CLOSE_ORDER_OPENED"
        ),
        PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE: "CLOSE_EXECUTED",
    }[stage]


def build_canary(stage, *, fault_injector=None, **request_changes):
    before, after = _graphs_for_stage(stage)
    loader = MutableGraphLoader(before)
    dry_loader = MutableGraphLoader(before)
    worker = AdvancingWorker(loader, after, stage, _child_outcome(stage))
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
        configuration_id=f"canary:configuration:{stage.value}",
    )
    run_id = f"canary-run-{stage.value.lower().replace('_', '-')}"
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
    fingerprint = paper_canary_graph_fingerprint(before, stage)
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
    nested = {
        "ingestion_request": None,
        "entry_execution_request": None,
        "exit_evaluation_request": None,
        "close_execution_request": None,
    }
    nested[
        {
            PaperControlledRuntimeCanaryStage.INGEST_COMMAND: "ingestion_request",
            PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY: "entry_execution_request",
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_NO_TRIGGER: (
                "exit_evaluation_request"
            ),
            PaperControlledRuntimeCanaryStage.EVALUATE_EXIT_TRIGGER: (
                "exit_evaluation_request"
            ),
            PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE: "close_execution_request",
        }[stage]
    ] = object()
    cycle = PaperLifecycleCycleRequest(
        cycle_id=f"cycle:{run_id}",
        contract_version=PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
        execution_mode=ExecutionMode.PAPER,
        explicit_paper_authorization=True,
        scope=PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP,
        max_stages=1,
        created_at=NOW,
        correlation_id=f"correlation:{run_id}",
        command_id=before.command_id,
        **nested,
    )
    values = {
        "request_id": f"request:{run_id}",
        "task_id": TASK_ID,
        "canary_run_id": run_id,
        "configuration": configuration,
        "target_identity": identity,
        "arming": arming,
        "cycle_request": cycle,
        "expected_initial_state": _state_for_stage(stage),
        "expected_stage": stage,
        "expected_graph_fingerprint": fingerprint,
        "expected_mutation_budget": (
            PaperControlledRuntimeCanaryMutationBudget.exact_for_stage(stage)
        ),
        "created_at": NOW,
        "evaluated_at": NOW,
        "correlation_id": cycle.correlation_id,
        "symbol": "BTCUSDT",
    }
    values.update(request_changes)
    request = PaperControlledRuntimeSingleCycleCanaryRequest(**values)
    service = PaperControlledRuntimeSingleCycleCanaryService(
        graph_loader=loader,
        dry_run_service=PaperControlledRuntimeDryRunService(dry_loader),
        worker=worker,
        target_validator=StaticTargetValidator(),
        fault_injector=fault_injector,
    )
    return request, service, worker, loader, dry_loader


@pytest.fixture
def lifecycle_graphs():
    return build_graphs()
