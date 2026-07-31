from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import inspect

import pytest

from app.engine_paper import controlled_runtime_sequence_canary as sequence
from app.engine_paper.controlled_runtime_canary import (
    PaperControlledRuntimeCanaryStage,
)


STAGES = tuple(PaperControlledRuntimeCanaryStage)


@pytest.mark.parametrize("case", range(700))
def test_bounded_sequence_contract_matrix_700_cases(case):
    stage = STAGES[case % len(STAGES)]
    budget = sequence.PaperControlledRuntimeSequenceMutationBudget.exact_for_stage(
        stage
    )
    assert sequence.MIN_SEQUENCE_STEPS == 1
    assert sequence.MAX_SEQUENCE_STEPS == 5
    assert sequence.MAX_WORKER_INVOCATIONS_PER_STEP == 1
    assert sequence.MAX_MUTATING_STAGES_PER_STEP == 1
    assert sequence.MAX_TOTAL_WORKER_INVOCATIONS == 5
    assert sequence.MAX_TOTAL_MUTATING_STAGES == 5
    assert budget == (
        sequence.PaperControlledRuntimeSequenceMutationBudget.exact_for_stage(
            stage
        )
    )
    assert budget + sequence.PaperControlledRuntimeSequenceMutationBudget() == budget
    assert all(
        isinstance(getattr(budget, name), int)
        for name in (
            "commands",
            "orders",
            "fills",
            "positions",
            "cursors",
            "exit_decisions",
            "order_events",
            "journal_rows",
            "entity_updates_versions",
            "fees",
            "pnl",
        )
    )
    with pytest.raises(FrozenInstanceError):
        budget.orders = case  # type: ignore[misc]


@pytest.mark.parametrize(
    "field",
    (
        "commands",
        "orders",
        "fills",
        "positions",
        "cursors",
        "exit_decisions",
        "order_events",
        "journal_rows",
        "entity_updates_versions",
        "fees",
        "pnl",
    ),
)
def test_mutation_budget_rejects_negative_or_boolean(field):
    values = {field: -1}
    with pytest.raises(ValueError):
        sequence.PaperControlledRuntimeSequenceMutationBudget(**values)
    values[field] = True
    with pytest.raises(ValueError):
        sequence.PaperControlledRuntimeSequenceMutationBudget(**values)


def test_sequence_source_is_structurally_bounded_and_has_no_child_services():
    source = inspect.getsource(sequence)
    assert "while " not in source
    assert "PaperCommandIngestionService" not in source
    assert "PaperOrderExecutionService" not in source
    assert "PaperExitEvaluationService" not in source
    assert ".commit(" not in source
    assert ".run_cycle(" not in source
    assert "for step_index in range(prefix, len(" in source
    assert "self._single_cycle_canary.run(single_request)" in source


def test_step_plan_is_frozen_bounded_and_non_secret():
    now = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
    step = sequence.PaperControlledRuntimeBoundedSequenceStepPlan(
        0,
        "step:0",
        __import__(
            "app.engine_paper.controlled_worker",
            fromlist=["PaperLifecycleState"],
        ).PaperLifecycleState.APPROVALS_ONLY,
        PaperControlledRuntimeCanaryStage.INGEST_COMMAND,
        __import__(
            "app.engine_paper.controlled_worker",
            fromlist=["PaperLifecycleState"],
        ).PaperLifecycleState.ENTRY_ORDER_OPEN,
        "input:0",
        sequence.PaperControlledRuntimeSequenceMutationBudget.exact_for_stage(
            PaperControlledRuntimeCanaryStage.INGEST_COMMAND
        ),
        now + timedelta(minutes=5),
        True,
    )
    with pytest.raises(FrozenInstanceError):
        step.step_id = "changed"  # type: ignore[misc]
    assert not any(
        token in {item.name for item in __import__("dataclasses").fields(step)}
        for token in ("password", "secret", "uri", "orm", "session")
    )


def test_all_public_result_tuples_are_hard_bounded():
    source = inspect.getsource(sequence)
    assert "steps[:MAX_SEQUENCE_STEPS]" in source
    assert "ordered_step_plans must be an immutable tuple" in source
    assert "ordered_cycle_requests must be an immutable tuple" in source
