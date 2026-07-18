from pathlib import Path

import pytest

from app.engine_market_data.operational import prod_smoke
from app.engine_market_data.prod_smoke import ProdSmokeRunner, find_repository_root


REQUIRED_MARKERS = (
    "pyproject.toml",
    "docker-compose.yml",
    "alembic.ini",
    "alembic",
    "scripts",
)


def make_repository(path: Path, *, missing: str | None = None) -> Path:
    path.mkdir()
    for marker in REQUIRED_MARKERS:
        if marker == missing:
            continue
        target = path / marker
        if marker in {"alembic", "scripts"}:
            target.mkdir()
        else:
            target.touch()
    return path


def assert_required_markers(root: Path) -> None:
    assert all((root / marker).exists() for marker in REQUIRED_MARKERS)


def test_discovers_repository_from_prod_smoke_module_file():
    root = find_repository_root(Path(prod_smoke.__file__))
    assert_required_markers(root)


def test_discovers_repository_from_operational_directory():
    root = find_repository_root(Path(prod_smoke.__file__).parent)
    assert_required_markers(root)


def test_discovers_repository_from_nested_temporary_path(tmp_path: Path):
    repository = make_repository(tmp_path / "repository")
    nested = repository / "app" / "package" / "operational"
    nested.mkdir(parents=True)
    assert find_repository_root(nested) == repository.resolve()


def test_runner_accepts_explicit_valid_repository_root(tmp_path: Path):
    repository = make_repository(tmp_path / "repository")
    runner = ProdSmokeRunner(tmp_path / "output", repository_root=repository)
    assert runner.root == repository.resolve()


def test_runner_rejects_explicit_invalid_repository_root(tmp_path: Path):
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    with pytest.raises(RuntimeError, match="Invalid repository root.*missing required markers"):
        ProdSmokeRunner(tmp_path / "output", repository_root=invalid)


@pytest.mark.parametrize("missing", REQUIRED_MARKERS)
def test_discovery_rejects_repository_missing_critical_marker(tmp_path: Path, missing: str):
    repository = make_repository(tmp_path / "repository", missing=missing)
    with pytest.raises(RuntimeError, match="Repository root could not be determined"):
        find_repository_root(repository)


def test_current_working_directory_does_not_affect_discovery(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = find_repository_root(Path(prod_smoke.__file__))
    assert_required_markers(root)


def test_resolved_root_contains_all_required_markers():
    assert_required_markers(find_repository_root(Path(prod_smoke.__file__)))


def test_alembic_check_accepts_actual_current_head(tmp_path: Path, monkeypatch):
    runner = ProdSmokeRunner(tmp_path / "output")
    outputs = iter((
        {"stdout": "0007_previous\n", "stderr": "", "exit_code": 0},
        {"stdout": "0008_current_head (head)\n", "stderr": "", "exit_code": 0},
        {"stdout": "", "stderr": "", "exit_code": 0},
        {"stdout": "0008_current_head (head)\n", "stderr": "", "exit_code": 0},
    ))
    monkeypatch.setattr(runner, "_run", lambda *_args, **_kwargs: next(outputs))
    result = runner.alembic_check()
    assert result["migration_applied"] is True
    assert result["target_revision"] == "0008_current_head"
