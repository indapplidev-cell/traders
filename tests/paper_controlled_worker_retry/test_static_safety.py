from __future__ import annotations

import ast
import inspect
from dataclasses import FrozenInstanceError, fields

import pytest

import app.engine_paper.controlled_worker as worker_module
from app.engine_paper.controlled_worker import (
    MAX_STAGE_SERVICE_ATTEMPTS,
    MAX_STAGES_PER_CYCLE,
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleResult,
    PaperLifecycleStageTrace,
    PaperLifecycleState,
    classify_paper_lifecycle_state,
)

from .conftest import make_cycle


@pytest.fixture(scope="module")
def source_and_tree():
    source = inspect.getsource(worker_module)
    return source, ast.parse(source)


@pytest.mark.parametrize(
    "forbidden",
    (
        "while True",
        "time.sleep",
        "asyncio.sleep",
        "requests.",
        "urllib",
        "httpx",
        "FastAPI",
        "Binance",
        "docker",
        "scheduler",
        "create_engine",
        ".commit()",
        "get_active_position",
        "latest",
    ),
)
def test_worker_source_excludes_forbidden_runtime_authorities(
    source_and_tree, forbidden
):
    source, _ = source_and_tree
    assert forbidden not in source


def test_worker_has_no_while_statement(source_and_tree):
    _, tree = source_and_tree
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))


def test_worker_has_no_async_or_recursive_cycle_call(source_and_tree):
    _, tree = source_and_tree
    assert not any(
        isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom))
        for node in ast.walk(tree)
    )
    run_cycle = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "run_cycle"
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run_cycle"
        for node in ast.walk(run_cycle)
    )


def test_classifier_has_no_calls_to_io_clock_or_random(source_and_tree):
    _, tree = source_and_tree
    classifier = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "classify_paper_lifecycle_state"
    )
    forbidden = {"open", "select", "datetime", "time", "random", "uuid4"}
    called = {
        node.func.id
        for node in ast.walk(classifier)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint(forbidden)


@pytest.mark.parametrize(
    "contract",
    (PaperLifecycleCycleRequest, PaperLifecycleCycleResult, PaperLifecycleStageTrace),
)
def test_public_cycle_contracts_are_frozen_and_slotted(contract):
    params = contract.__dataclass_params__
    assert params.frozen is True
    assert "__slots__" in contract.__dict__


def test_cycle_request_rejects_mutation(lifecycle_graphs):
    request = make_cycle(lifecycle_graphs.command.command_id)
    with pytest.raises(FrozenInstanceError):
        request.command_id = "command:mutated"


def test_cycle_result_excludes_orm_sql_candles_and_tracebacks():
    names = {item.name for item in fields(PaperLifecycleCycleResult)}
    assert names.isdisjoint(
        {
            "orm",
            "session",
            "sql",
            "candles",
            "approval_payload",
            "traceback",
            "exception",
            "secret",
        }
    )


def test_bounds_and_attempt_policy_are_finite():
    assert MAX_STAGES_PER_CYCLE == 4
    assert MAX_STAGE_SERVICE_ATTEMPTS == 1


def test_classifier_signature_is_single_graph_argument():
    signature = inspect.signature(classify_paper_lifecycle_state)
    assert tuple(signature.parameters) == ("graph",)
    assert len(PaperLifecycleState) == 6
