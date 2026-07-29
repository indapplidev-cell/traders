from __future__ import annotations

import ast
import inspect
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from app.engine_execution.paper_state_machine import ORDER_TRANSITION_EVENT_TYPES
from app.engine_paper.paper_approvals import (
    PaperCommandApprovalCompatibility,
    PaperQuantityApproval,
    PaperRiskApproval,
    PaperStrategyApproval,
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    issue_paper_quantity_approval,
)
from app.engine_safety.paper_domain import ExecutionMode, parse_execution_mode


ROOT = Path(__file__).parents[2]
APPROVAL_SOURCE = ROOT / "app/engine_paper/paper_approvals.py"


def test_approval_authorities_have_no_wall_clock_random_db_or_network_imports():
    tree = ast.parse(APPROVAL_SOURCE.read_text(encoding="utf-8"))
    forbidden_roots = {
        "random",
        "secrets",
        "uuid",
        "time",
        "sqlalchemy",
        "psycopg",
        "requests",
        "httpx",
        "socket",
        "urllib",
    }
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported.isdisjoint(forbidden_roots)


def test_approval_authorities_do_not_call_now_utcnow_random_or_uuid():
    tree = ast.parse(APPROVAL_SOURCE.read_text(encoding="utf-8"))
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called_attributes.isdisjoint(
        {"now", "utcnow", "time", "random", "randint", "uuid4", "token_urlsafe"}
    )


def test_approval_module_has_no_global_mutable_collections():
    tree = ast.parse(APPROVAL_SOURCE.read_text(encoding="utf-8"))
    mutable_nodes = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            assert not isinstance(node.value, mutable_nodes)


def test_authority_inputs_expose_no_unbounded_collection_parameters():
    for authority in (
        finalize_paper_strategy_approval,
        issue_paper_quantity_approval,
        finalize_paper_risk_approval,
    ):
        annotations = {
            str(parameter.annotation)
            for parameter in inspect.signature(authority).parameters.values()
        }
        assert not any(
            marker in annotation
            for annotation in annotations
            for marker in ("list", "dict", "Sequence", "Iterable", "Collection")
        )


def test_all_approval_and_compatibility_monetary_fields_are_decimal():
    expected = {
        PaperStrategyApproval: {
            "entry_reference_price",
            "stop_price",
            "target_price",
        },
        PaperQuantityApproval: {"approved_quantity"},
        PaperRiskApproval: {"approved_quantity"},
        PaperCommandApprovalCompatibility: {
            "entry_reference_price",
            "stop_price",
            "target_price",
            "approved_quantity",
        },
    }
    for contract, monetary_names in expected.items():
        annotations = {field.name: field.type for field in fields(contract)}
        assert {name for name in monetary_names if annotations[name] == "Decimal"} == monetary_names


def test_approval_module_never_constructs_command_or_order():
    source = APPROVAL_SOURCE.read_text(encoding="utf-8")
    assert "PaperExecutionCommand(" not in source
    assert "PaperOrder(" not in source
    assert "create_paper_order(" not in source


def test_global_execution_default_remains_off():
    assert parse_execution_mode(None) is ExecutionMode.OFF


def test_transition_event_mapping_is_read_only_global_state():
    assert isinstance(ORDER_TRANSITION_EVENT_TYPES, MappingProxyType)


def test_integrated_migration_0009_has_no_worktree_diff():
    import subprocess

    result = subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            "--",
            "alembic/versions/0009_paper_trading_persistence_foundation.py",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
