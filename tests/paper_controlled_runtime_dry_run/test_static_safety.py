from __future__ import annotations

import ast
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

from app.engine_paper.controlled_runtime import (
    MAX_ALLOWED_SYMBOLS,
    MAX_CONFIGURATION_FILE_BYTES,
    PaperControlledRuntimeConfiguration,
    PaperControlledRuntimeDryRunPlanItem,
    PaperControlledRuntimeDryRunRequest,
    PaperControlledRuntimeDryRunResult,
    PaperControlledRuntimeReadOnlyProofSummary,
    PaperControlledRuntimeStartupGateResult,
)


SOURCE_PATH = Path("app/engine_paper/controlled_runtime.py")
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


@pytest.mark.parametrize(
    "contract_type",
    (
        PaperControlledRuntimeConfiguration,
        PaperControlledRuntimeStartupGateResult,
        PaperControlledRuntimeDryRunRequest,
        PaperControlledRuntimeDryRunPlanItem,
        PaperControlledRuntimeReadOnlyProofSummary,
        PaperControlledRuntimeDryRunResult,
    ),
)
def test_public_contracts_are_frozen_slotted_dataclasses(contract_type):
    assert is_dataclass(contract_type)
    assert contract_type.__dataclass_params__.frozen is True
    assert "__slots__" in contract_type.__dict__


def test_no_unbounded_loop_or_recursive_call_exists():
    assert not any(isinstance(node, (ast.While, ast.AsyncFor)) for node in ast.walk(TREE))
    functions = {
        node.name: node
        for node in ast.walk(TREE)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for name, node in functions.items():
        assert not any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == name
            for child in ast.walk(node)
        )


@pytest.mark.parametrize(
    "forbidden",
    (
        "while True",
        "docker compose",
        "os.environ",
        "getenv(",
        ".env",
        "requests.",
        "httpx.",
        "socket.",
        "PaperCommandIngestionService(",
        "PaperOrderExecutionService(",
        "PaperExitEvaluationService(",
        ".commit(",
        ".flush(",
        "with_for_update",
        "FOR UPDATE",
    ),
)
def test_runtime_module_contains_no_ambient_or_mutating_capability(forbidden):
    assert forbidden not in SOURCE


def test_dry_run_service_constructor_has_no_mutating_dependency_parameters():
    service = next(
        node
        for node in TREE.body
        if isinstance(node, ast.ClassDef) and node.name == "PaperControlledRuntimeDryRunService"
    )
    init = next(node for node in service.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
    assert [argument.arg for argument in init.args.args] == ["self", "graph_loader"]


def test_result_has_explicit_zero_mutation_counters():
    names = {item.name for item in fields(PaperControlledRuntimeDryRunResult)}
    assert {"business_mutation_count", "commit_count", "child_mutation_call_count"} <= names


def test_all_collection_bounds_are_hard_and_small():
    assert MAX_ALLOWED_SYMBOLS <= 32
    assert MAX_CONFIGURATION_FILE_BYTES == 64 * 1024


def test_module_defines_no_mutable_global_literal():
    for node in TREE.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            assert not isinstance(value, (ast.Dict, ast.List, ast.Set))


def test_runtime_contract_introduces_no_float_monetary_field():
    assert not any(
        isinstance(node, ast.Name) and node.id == "float" for node in ast.walk(TREE)
    )
