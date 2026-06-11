import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import build_model_quality_validation_preview_payload, cli


def test_build_model_quality_validation_preview_payload() -> None:
    payload = build_model_quality_validation_preview_payload()

    assert payload["quality_status"] == "NEEDS_MORE_DATA"
    assert payload["sample_mode"] is True
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False


def test_model_quality_validation_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["model-quality-validation-preview"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["sample_mode"] is True
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False


def test_model_quality_validation_export_cli_writes_json(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "model_quality_validation_report.json"

    result = runner.invoke(
        cli,
        [
            "model-quality-validation-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload["status"] == "ok"
    assert command_payload["quality_status"] == "NEEDS_MORE_DATA"
    assert command_payload["approved_for_live_trading"] is False
    assert command_payload["approved_for_auto_activation"] is False
    assert command_payload["sample_mode"] is True

    assert file_payload["quality_status"] == "NEEDS_MORE_DATA"
    assert file_payload["sample_mode"] is True
    assert file_payload["approved_for_live_trading"] is False
    assert file_payload["approved_for_auto_activation"] is False
