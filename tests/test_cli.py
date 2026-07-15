import json

from typer.testing import CliRunner

from app.cli.commands import build_health_payload, cli
from app.config.settings import get_settings
from app.db.session import reset_engine_cache

runner = CliRunner()


def test_cli_health() -> None:
    result = runner.invoke(cli, ["health"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == build_health_payload()


def test_cli_db_check(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    get_settings.cache_clear()
    reset_engine_cache()

    try:
        result = runner.invoke(cli, ["db-check"])
    finally:
        # ``monkeypatch`` restores the environment after this test, while the
        # lru-cached Settings object would otherwise leak SQLite into later
        # PostgreSQL integration audits in the same pytest process.
        get_settings.cache_clear()
        reset_engine_cache()

    assert result.exit_code == 0
    assert "db-check: ok" in result.stdout
