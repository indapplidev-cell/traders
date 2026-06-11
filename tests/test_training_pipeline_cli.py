import json
from pathlib import Path

from typer.testing import CliRunner

import app.cli.commands as commands_module
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


def test_train_quality_pipeline_cli_real_mode_uses_pipeline_entrypoint(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_train_quality_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "status": "COMPLETED",
            "run_id": "cli_real_case",
            "symbol": kwargs["symbol"],
            "interval": kwargs["interval"],
            "start_date": kwargs["start_date"],
            "end_date": "2025-01-10",
            "dry_run": False,
            "sample_mode": False,
            "stage_count": 16,
            "completed_stage_count": 16,
            "failed_stage_count": 0,
            "skipped_stage_count": 0,
            "quality_status": "NEEDS_MORE_DATA",
            "approved_for_traders_core_integration": False,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "output_dir": str(tmp_path / "training_pipeline_runs" / "cli_real_case"),
            "log_path": str(tmp_path / "training_pipeline_runs" / "cli_real_case" / "training_pipeline.log"),
            "events_path": str(tmp_path / "training_pipeline_runs" / "cli_real_case" / "training_pipeline_events.jsonl"),
            "json_report_path": str(tmp_path / "training_pipeline_runs" / "cli_real_case" / "training_pipeline_report.json"),
            "markdown_report_path": str(tmp_path / "training_pipeline_runs" / "cli_real_case" / "training_pipeline_report.md"),
        }

    monkeypatch.setattr(commands_module, "run_train_quality_pipeline", fake_run_train_quality_pipeline)

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
            "--end-date",
            "2025-01-10",
            "--run-id",
            "cli_real_case",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)

    assert payload["status"] == "COMPLETED"
    assert payload["skipped_stage_count"] == 0
    assert captured["dry_run"] is False
    assert captured["sample_mode"] is False
    assert captured["run_id"] == "cli_real_case"
