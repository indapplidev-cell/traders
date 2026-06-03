from __future__ import annotations

import ast
from pathlib import Path


def _extract_revision(path: Path) -> str | None:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    for node in module.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != "revision":
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value

    return None


def test_alembic_revision_ids_fit_postgresql_version_table() -> None:
    versions_dir = Path("alembic/versions")
    version_files = sorted(path for path in versions_dir.glob("*.py") if path.name != "__init__.py")

    assert version_files, "No Alembic migration files found in alembic/versions."

    too_long: list[str] = []
    missing: list[str] = []

    for path in version_files:
        revision = _extract_revision(path)
        if revision is None:
            missing.append(path.name)
            continue
        if len(revision) > 32:
            too_long.append(f"{path.name}: '{revision}' ({len(revision)} chars)")

    assert not missing, f"Missing revision variable in Alembic migration files: {', '.join(missing)}"
    assert not too_long, "Alembic revision ids must be <= 32 chars: " + "; ".join(too_long)
