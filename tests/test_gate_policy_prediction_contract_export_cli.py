import json

from typer.testing import CliRunner

from app.cli.commands import export_gate_policy_prediction_contract_report, cli


def test_export_gate_policy_prediction_contract_report_writes_json_file(tmp_path) -> None:
    output_path = tmp_path / "gate_policy_prediction_contract_report.json"

    result = export_gate_policy_prediction_contract_report(output_path)

    assert result["status"] == "ok"
    assert result["output_path"] == str(output_path)

    assert result["contract_name"] == "gate_policy_prediction_payload"
    assert result["version"] == "ml16.1"
    assert result["required_count"] == 4
    assert result["optional_count"] == 7
    assert result["all_field_count"] == 11
    assert result["alias_field_count"] == 11
    assert result["direction_alias_count"] == 10
    assert result["known_regime_count"] == 8

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["version"] == "ml16.1"

    assert payload["required_fields"] == [
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
    ]

    assert "risk_score" in payload["optional_fields"]
    assert "expected_move_atr" in payload["optional_fields"]
    assert "model_total_r" in payload["optional_fields"]

    assert payload["field_aliases"]["sample_count"] == [
        "sample_count",
        "samples",
        "n",
    ]

    assert payload["direction_aliases"]["UP"] == "LONG"
    assert payload["direction_aliases"]["DOWN"] == "SHORT"

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_contract_export_cli_writes_json_file(tmp_path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "cli_gate_policy_prediction_contract_report.json"

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-contract-export",
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

    assert command_payload["contract_name"] == "gate_policy_prediction_payload"
    assert command_payload["version"] == "ml16.1"
    assert command_payload["required_count"] == 4
    assert command_payload["optional_count"] == 7
    assert command_payload["all_field_count"] == 11
    assert command_payload["alias_field_count"] == 11
    assert command_payload["direction_alias_count"] == 10
    assert command_payload["known_regime_count"] == 8

    assert file_payload["contract_name"] == "gate_policy_prediction_payload"
    assert file_payload["version"] == "ml16.1"

    assert file_payload["required_fields"] == [
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
    ]

    assert file_payload["direction_aliases"]["BUY"] == "LONG"
    assert file_payload["direction_aliases"]["SELL"] == "SHORT"

    assert file_payload["integration_status"]["database_connected"] is False
    assert file_payload["integration_status"]["traders_core_connected"] is False
