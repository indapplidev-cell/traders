from pathlib import Path

from validation.engine_market_data_04_prod_smoke import validate_runtime_independence


ROOT = Path(__file__).parents[1]


def test_runtime_is_cli_managed_and_restart_ready_without_developer_session():
    result = validate_runtime_independence(
        (ROOT / "docker-compose.yml").read_text(encoding="utf-8"),
        (ROOT / "docs/operations/engine_market_data_04_systemd.md").read_text(encoding="utf-8"),
    )
    assert result["docker_systemd_ready"]
    assert result["runtime_requires_codex"] is False
    assert result["runtime_requires_vscode"] is False
    assert result["runtime_requires_notebook"] is False
    assert result["runtime_requires_interactive_developer_session"] is False
