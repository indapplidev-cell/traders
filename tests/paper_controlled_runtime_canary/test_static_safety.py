from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from app.engine_paper.controlled_runtime_canary import (
    PaperControlledRuntimeSingleCycleCanaryResult,
)


ROOT = Path(__file__).resolve().parents[2]
CANARY = ROOT / "app" / "engine_paper" / "controlled_runtime_canary.py"


def _tree():
    return ast.parse(CANARY.read_text(encoding="utf-8"))


def test_canary_source_has_no_while_or_async_background_loop():
    tree = _tree()
    assert not any(isinstance(node, (ast.While, ast.AsyncFor)) for node in ast.walk(tree))


def test_canary_source_has_no_sleep_poll_scheduler_daemon_api_or_exchange_import():
    tree = _tree()
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "time",
        "asyncio",
        "schedule",
        "apscheduler",
        "fastapi",
        "requests",
        "httpx",
        "websockets",
        "binance",
    }
    assert not imported & forbidden


def test_canary_has_no_float_literals_or_float_annotations():
    tree = _tree()
    assert not any(
        isinstance(node, ast.Constant) and isinstance(node.value, float)
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, ast.Name) and node.id == "float" for node in ast.walk(tree)
    )


def test_canary_has_no_module_level_mutable_collection_assignments():
    tree = _tree()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            assert not isinstance(node.value, (ast.List, ast.Dict, ast.Set))


def test_canary_does_not_import_orm_models_or_business_repositories():
    source = CANARY.read_text(encoding="utf-8")
    assert "app.db.paper_models" not in source
    assert "PaperRepositories" not in source
    assert "Session.commit" not in source
    assert ".commit(" not in source


def test_canary_has_exactly_one_worker_run_cycle_call_site():
    tree = _tree()
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run_cycle"
    ]
    assert len(calls) == 1


def test_canary_result_has_no_sensitive_or_unbounded_payload_fields():
    names = {item.name.lower() for item in fields(PaperControlledRuntimeSingleCycleCanaryResult)}
    assert not names & {
        "password",
        "secret",
        "token",
        "database_url",
        "uri",
        "raw_sql",
        "traceback",
        "candles",
        "approvals",
        "configuration",
        "orm_objects",
    }


def test_no_schema_or_migration_file_is_part_of_canary_module():
    assert "alembic" not in str(CANARY.relative_to(ROOT)).lower()
    assert "migration" not in CANARY.name.lower()
