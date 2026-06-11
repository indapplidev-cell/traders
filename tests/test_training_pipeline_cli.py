import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli


def test_train_quality_pipeline_cli_dry_run_creates_runtime_files(tmp_path: Path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "training_pipeline_runs"

    result = runner.invoke(
        cli,
        [
            "train-quality-pipeline",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--start-date",
            "2025-01-01",
            "--run-id",
            "cli_dry_run_case",
            "--dry-run",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["status"] == "DRY_RUN_COMPLETED"
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
    assert Path(payload["output_dir"]).exists()
    assert Path(payload["log_path"]).exists()
    assert Path(payload["events_path"]).exists()
    assert Path(payload["json_report_path"]).exists()
    assert Path(payload["markdown_report_path"]).exists()
