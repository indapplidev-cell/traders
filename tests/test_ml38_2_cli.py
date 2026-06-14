import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli


def test_ml38_2_fv3_tuning_preview_cli_returns_required_json() -> None:
    result = CliRunner().invoke(cli, ["ml38-2-fv3-tuning-preview"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["stage"] == "ML38.2"
    assert payload["feature_version"] == "fv3_candle_ta_context"
    assert payload["config_count"] >= 6
    assert payload["required_symbols"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    assert payload["safety"]["traders_core_integration"] is False


def test_ml38_2_fv3_tuning_run_cli_dry_run_creates_outputs(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli,
        [
            "ml38-2-fv3-tuning-run",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--start-date",
            "2025-01-01",
            "--dry-run",
            "--max-configs",
            "2",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["feature_version_used"] == "fv3_candle_ta_context"
    assert payload["experiment_status"] == "DRY_RUN_COMPLETED"
    assert Path(payload["summary_json_path"]).exists()
