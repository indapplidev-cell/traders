import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli


def test_model_anti_collapse_preview_cli_detects_collapse() -> None:
    result = CliRunner().invoke(cli, ["model-anti-collapse-preview"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["collapse_detected"] is True


def test_model_candidate_select_preview_cli_rejects_bad_candidate() -> None:
    result = CliRunner().invoke(cli, ["model-candidate-select-preview"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["candidate_status"] == "CANDIDATE_REJECTED"


def test_label_quality_grid_preview_cli_outputs_configs() -> None:
    result = CliRunner().invoke(cli, ["label-quality-grid-preview"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["config_count"] >= 5


def test_ml27_export_commands_write_files(tmp_path: Path) -> None:
    runner = CliRunner()
    anti_path = tmp_path / "anti.json"
    candidate_path = tmp_path / "candidate.json"
    grid_path = tmp_path / "grid.json"

    anti_result = runner.invoke(cli, ["model-anti-collapse-export", "--output-path", str(anti_path)])
    candidate_result = runner.invoke(cli, ["model-candidate-select-export", "--output-path", str(candidate_path)])
    grid_result = runner.invoke(cli, ["label-quality-grid-export", "--output-path", str(grid_path)])

    assert anti_result.exit_code == 0
    assert candidate_result.exit_code == 0
    assert grid_result.exit_code == 0
    assert json.loads(anti_path.read_text(encoding="utf-8"))["collapse_detected"] is True
    assert json.loads(candidate_path.read_text(encoding="utf-8"))["candidate_status"] == "CANDIDATE_REJECTED"
    assert json.loads(grid_path.read_text(encoding="utf-8"))["config_count"] >= 5
