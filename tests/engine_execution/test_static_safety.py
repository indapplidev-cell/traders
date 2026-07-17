from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_FILES = [
    *sorted((ROOT / "app" / "engine_execution").rglob("*.py")),
    ROOT / "scripts" / "engine_execution_dry_run.py",
]
FORBIDDEN_IMPORT_ROOTS = {
    "requests", "httpx", "aiohttp", "websockets", "docker", "subprocess",
    "socket", "urllib", "binance",
}
FORBIDDEN_CALL_NAMES = {
    "create_order", "order_market", "order_limit", "system", "post",
}
FORBIDDEN_CREDENTIAL_NAMES = {
    "BINANCE_API_KEY", "BINANCE_API_SECRET", "api_key", "api_secret",
}


def test_runtime_ast_has_no_network_container_or_process_imports():
    violations = []
    for path in RUNTIME_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
                if roots & FORBIDDEN_IMPORT_ROOTS:
                    violations.append((path.name, node.lineno, sorted(roots & FORBIDDEN_IMPORT_ROOTS)))
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    violations.append((path.name, node.lineno, root))
    assert violations == []


def test_runtime_ast_has_no_private_exchange_or_credential_operations():
    violations = []
    for path in RUNTIME_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.attr if isinstance(node.func, ast.Attribute) else (
                    node.func.id if isinstance(node.func, ast.Name) else "")
                if name in FORBIDDEN_CALL_NAMES:
                    violations.append((path.name, node.lineno, name))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in FORBIDDEN_CREDENTIAL_NAMES:
                    violations.append((path.name, node.lineno, node.value))
    assert violations == []


def test_runtime_import_boundary_allows_only_engine_paper_project_adapter():
    project_imports = set()
    for path in RUNTIME_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                project_imports.add(node.module)
    assert all(name.startswith("app.engine_execution") or name == "app.engine_paper"
               for name in project_imports)
