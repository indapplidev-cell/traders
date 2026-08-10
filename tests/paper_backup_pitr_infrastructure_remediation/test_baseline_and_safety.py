from __future__ import annotations

import ast
from pathlib import Path

from app.engine_paper import backup_pitr_infrastructure as infra


ROOT = Path(__file__).resolve().parents[2]


def test_exact_authoritative_baseline_and_all_22_hashes_are_pinned() -> None:
    assert infra.EXPECTED_SERVER_HEAD == "8261813645e1f2c4a603ac8a58bfabfb0d4f926b"
    assert infra.EXPECTED_SERVER_TREE == "29fb3865378d055fcb010f3cb86d25ff4b2ef1f4"
    assert len(infra.EXPECTED_EVIDENCE_HASHES) == 22
    for digest in infra.EXPECTED_EVIDENCE_HASHES.values():
        assert len(digest) == 64
        int(digest, 16)


def test_no_foundation_migration_or_reconciliation_semantics_changed_by_module() -> None:
    source = (ROOT / "app" / "engine_paper" / "backup_pitr_infrastructure.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "app.engine_paper.reconciliation" not in imports
    assert "app.engine_paper.repository" not in imports
    assert "app.engine_paper.controlled_worker" not in imports


def test_contract_source_contains_no_executable_production_adapter() -> None:
    source = (ROOT / "app" / "engine_paper" / "backup_pitr_infrastructure.py").read_text(encoding="utf-8").casefold()
    for forbidden in ("subprocess", "sqlalchemy", "docker", "psycopg", "urlopen", "os.environ"):
        assert forbidden not in source


def test_safe_inspector_contains_no_forbidden_environment_template() -> None:
    source = (ROOT / "scripts" / "safe_production_inspector.py").read_text(encoding="utf-8")
    for forbidden in (".Config.Env", ".ContainerConfig.Env", "docker compose config", "printenv"):
        assert forbidden not in source
