import json

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_prediction_mapping_plan_preview_payload,
    cli,
)


def test_build_gate_policy_prediction_mapping_plan_preview_payload() -> None:
    payload = build_gate_policy_prediction_mapping_plan_preview_payload()

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"

    assert payload["required_target_count"] == 4
    assert payload["optional_target_count"] == 5
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

    assert payload["optional_target_fields"] == [
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    assert "prob_up" in payload["all_source_fields"]
    assert "prob_down" in payload["all_source_fields"]
    assert "prob_flat" in payload["all_source_fields"]
    assert "confidence" in payload["all_source_fields"]
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


def test_gate_policy_prediction_mapping_plan_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-mapping-plan-preview",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["name"] == "gate_policy_prediction_payload_mapping"
    assert payload["version"] == "ml19.1"

    assert payload["required_target_count"] == 4
    assert payload["optional_target_count"] == 5
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

    assert payload["optional_target_fields"] == [
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    assert payload["direction_outputs"] == [
        "LONG",
        "SHORT",
        "FLAT",
        "NONE",
    ]

    assert "prob_up" in payload["all_source_fields"]
    assert "prob_down" in payload["all_source_fields"]
    assert "prob_flat" in payload["all_source_fields"]
    assert "confidence" in payload["all_source_fields"]
    assert "tp_before_sl_probability" in payload["all_source_fields"]

    assert "mapping_rules" not in payload
    assert "direction_rules" not in payload
    assert "all_target_fields" not in payload

    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_gate_policy_prediction_mapping_plan_preview_has_consistent_optional_fields() -> None:
    payload = build_gate_policy_prediction_mapping_plan_preview_payload()

    assert payload["optional_target_count"] == len(payload["optional_target_fields"])

    assert payload["optional_target_fields"] == [
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    assert "expected_move_atr" in payload["optional_target_fields"]
    assert "model_version" in payload["optional_target_fields"]


def test_gate_policy_prediction_mapping_plan_preview_cli_has_consistent_optional_fields() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-prediction-mapping-plan-preview",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["optional_target_count"] == len(payload["optional_target_fields"])

    assert payload["optional_target_fields"] == [
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    assert "expected_move_atr" in payload["optional_target_fields"]
    assert "model_version" in payload["optional_target_fields"]
