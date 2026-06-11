import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    cli,
    export_gate_policy_prediction_mapping_plan_summary_report,
)


EXPECTED_OPTIONAL_TARGET_FIELDS = [
    "risk_score",
    "expected_move_atr",
    "model_version",
    "symbol",
    "interval",
]


def test_export_gate_policy_prediction_mapping_plan_summary_report_writes_json_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "gate_policy_prediction_mapping_plan_summary.json"

    summary = export_gate_policy_prediction_mapping_plan_summary_report(
        output_path=output_path,
    )

    assert summary["status"] == "ok"
    assert summary["output_path"] == str(output_path)
    assert summary["name"] == "gate_policy_prediction_payload_mapping"
    assert summary["version"] == "ml19.1"
    assert summary["required_target_count"] == 4
    assert summary["optional_target_count"] == 5
    assert summary["all_target_count"] == 9
    assert summary["all_source_count"] == 13
    assert summary["mapping_rule_count"] == 9
    assert summary["direction_rule_count"] == 4
    assert summary["runtime_adapter_implemented"] is False

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"

    assert payload["required_target_count"] == 4
    assert payload["optional_target_count"] == 5
    assert payload["optional_target_count"] == len(payload["optional_target_fields"])
    assert payload["all_target_count"] == 9
    assert payload["all_source_count"] == 13
    assert payload["mapping_rule_count"] == 9
    assert payload["direction_rule_count"] == 4

    assert payload["required_target_fields"] == [
        "direction",
        "confidence",
        "tp_before_sl_probability",
        "regime",
    ]

    assert payload["optional_target_fields"] == EXPECTED_OPTIONAL_TARGET_FIELDS

    assert "prob_up" in payload["all_source_fields"]
    assert "prob_down" in payload["all_source_fields"]
    assert "prob_flat" in payload["all_source_fields"]
    assert "confidence" in payload["all_source_fields"]
    assert "expected_move_atr" in payload["all_source_fields"]
    assert "model_version" in payload["all_source_fields"]
    assert "tp_before_sl_probability" in payload["all_source_fields"]

    assert payload["direction_outputs"] == [
        "LONG",
        "SHORT",
        "FLAT",
        "NONE",
    ]

    assert "mapping_rules" not in payload
    assert "direction_rules" not in payload
    assert "all_target_fields" not in payload

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_gate_policy_prediction_mapping_plan_export_cli_writes_json_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "cli_gate_policy_prediction_mapping_plan_summary.json"

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-mapping-plan-export",
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
    assert command_payload["name"] == "gate_policy_prediction_payload_mapping"
    assert command_payload["version"] == "ml19.1"
    assert command_payload["required_target_count"] == 4
    assert command_payload["optional_target_count"] == 5
    assert command_payload["all_target_count"] == 9
    assert command_payload["all_source_count"] == 13
    assert command_payload["mapping_rule_count"] == 9
    assert command_payload["direction_rule_count"] == 4
    assert command_payload["runtime_adapter_implemented"] is False

    assert file_payload["optional_target_count"] == 5
    assert file_payload["optional_target_count"] == len(file_payload["optional_target_fields"])
    assert file_payload["optional_target_fields"] == EXPECTED_OPTIONAL_TARGET_FIELDS

    assert "expected_move_atr" in file_payload["optional_target_fields"]
    assert "model_version" in file_payload["optional_target_fields"]
    assert "symbol" in file_payload["optional_target_fields"]
    assert "interval" in file_payload["optional_target_fields"]

    assert "mapping_rules" not in file_payload
    assert "direction_rules" not in file_payload
    assert "all_target_fields" not in file_payload

    assert file_payload["integration_status"]["runtime_adapter_implemented"] is False
