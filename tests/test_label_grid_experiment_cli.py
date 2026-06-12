import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli


def test_label_grid_experiment_preview_cli_returns_json() -> None:
    result = CliRunner().invoke(cli, ["label-grid-experiment-preview"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["available_label_configs"]


def test_label_grid_experiment_run_cli_dry_run_and_sample_mode_create_outputs(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    dry_dir = tmp_path / "dry"
    sample_dir = tmp_path / "sample"

    dry_result = runner.invoke(
        cli,
        [
            "label-grid-experiment-run",
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
            str(dry_dir),
        ],
    )
    sample_result = runner.invoke(
        cli,
        [
            "label-grid-experiment-run",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--start-date",
            "2025-01-01",
            "--sample-mode",
            "--max-configs",
            "2",
            "--output-dir",
            str(sample_dir),
        ],
    )

    assert dry_result.exit_code == 0
    assert sample_result.exit_code == 0

    dry_payload = json.loads(dry_result.stdout)
    sample_payload = json.loads(sample_result.stdout)

    assert dry_payload["experiment_status"] == "DRY_RUN_COMPLETED"
    assert sample_payload["experiment_status"] == "SAMPLE_COMPLETED"
    assert Path(sample_payload["summary_json_path"]).exists()
    assert Path(sample_payload["summary_markdown_path"]).exists()
