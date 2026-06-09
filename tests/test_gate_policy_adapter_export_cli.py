import json

from typer.testing import CliRunner

from app.cli.commands import export_gate_policy_adapter_preview_report, cli


def test_export_gate_policy_adapter_preview_report_writes_json_file(tmp_path) -> None:
    output_path = tmp_path / "gate_policy_adapter_preview_report.json"

    result = export_gate_policy_adapter_preview_report(output_path)

    assert result["status"] == "ok"
    assert result["output_path"] == str(output_path)

    assert result["raw_payload_count"] == 4
    assert result["input_count"] == 4
    assert result["result_count"] == 4
    assert result["total"] == 4
    assert result["allowed_total"] == 2
    assert result["blocked_total"] == 2

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["raw_payload_count"] == 4
    assert payload["input_count"] == 4
    assert payload["result_count"] == 4

    assert payload["report"]["total"] == 4
    assert payload["report"]["allowed_total"] == 2
    assert payload["report"]["blocked_total"] == 2

    assert payload["decision_sequence"] == [
        "ALLOW_LONG",
        "ALLOW_SHORT",
        "BAD_REGIME",
        "LOW_CONFIDENCE",
    ]

    assert payload["allowed_sequence"] == [
        True,
        True,
        False,
        False,
    ]


def test_gate_policy_adapter_export_cli_writes_json_file(tmp_path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "cli_gate_policy_adapter_preview_report.json"

    result = runner.invoke(
        cli,
        [
            "gate-policy-adapter-export",
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
    assert command_payload["raw_payload_count"] == 4
    assert command_payload["input_count"] == 4
    assert command_payload["result_count"] == 4
    assert command_payload["total"] == 4
    assert command_payload["allowed_total"] == 2
    assert command_payload["blocked_total"] == 2

    assert file_payload["raw_payload_count"] == 4
    assert file_payload["input_count"] == 4
    assert file_payload["result_count"] == 4

    assert file_payload["report"]["total"] == 4
    assert file_payload["report"]["allowed_total"] == 2
    assert file_payload["report"]["blocked_total"] == 2

    assert file_payload["decision_sequence"] == [
        "ALLOW_LONG",
        "ALLOW_SHORT",
        "BAD_REGIME",
        "LOW_CONFIDENCE",
    ]
