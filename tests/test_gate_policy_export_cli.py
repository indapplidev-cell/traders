import json

from typer.testing import CliRunner

from app.cli.commands import export_gate_policy_smoke_report, cli


def test_export_gate_policy_smoke_report_writes_json_file(tmp_path) -> None:
    output_path = tmp_path / "gate_policy_report.json"

    result = export_gate_policy_smoke_report(output_path)

    assert result["status"] == "ok"
    assert result["output_path"] == str(output_path)
    assert result["total"] == 5
    assert result["allowed_total"] == 2
    assert result["blocked_total"] == 3

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["total"] == 5
    assert payload["allowed_total"] == 2
    assert payload["blocked_total"] == 3
    assert payload["decision_counts"]["ALLOW_LONG"] == 1
    assert payload["decision_counts"]["ALLOW_SHORT"] == 1
    assert payload["decision_counts"]["BAD_REGIME"] == 1
    assert payload["decision_counts"]["LOW_CONFIDENCE"] == 1
    assert payload["decision_counts"]["BLOCK"] == 1


def test_gate_policy_export_cli_writes_json_file(tmp_path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "cli_gate_policy_report.json"

    result = runner.invoke(
        cli,
        [
            "gate-policy-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload["status"] == "ok"
    assert command_payload["output_path"] == str(output_path)
    assert command_payload["total"] == 5
    assert command_payload["allowed_total"] == 2
    assert command_payload["blocked_total"] == 3

    assert file_payload["total"] == 5
    assert file_payload["allowed_total"] == 2
    assert file_payload["blocked_total"] == 3
