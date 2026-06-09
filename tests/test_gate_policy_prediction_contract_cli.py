import json

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_prediction_contract_preview_payload,
    cli,
)


def test_build_gate_policy_prediction_contract_preview_payload() -> None:
    payload = build_gate_policy_prediction_contract_preview_payload()

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["version"] == "ml16.1"

    assert payload["required_count"] == 4
    assert payload["optional_count"] == 7
    assert payload["all_field_count"] == 11

    assert payload["required_fields"] == [
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
    ]

    assert "risk_score" in payload["optional_fields"]
    assert "expected_move_atr" in payload["optional_fields"]
    assert "model_total_r" in payload["optional_fields"]

    assert payload["field_aliases"]["regime"] == [
        "regime",
        "market_regime",
        "detected_regime",
    ]

    assert payload["field_aliases"]["direction"] == [
        "direction",
        "predicted_direction",
        "signal_direction",
        "side",
    ]

    assert payload["direction_aliases"]["BUY"] == "LONG"
    assert payload["direction_aliases"]["SELL"] == "SHORT"

    assert "trend_up" in payload["known_regime_values"]
    assert "unknown" in payload["known_regime_values"]

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_contract_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["gate-policy-prediction-contract-preview"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["version"] == "ml16.1"

    assert payload["required_count"] == 4
    assert payload["optional_count"] == 7
    assert payload["all_field_count"] == 11
    assert payload["alias_field_count"] == 11

    assert payload["required_fields"] == [
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
    ]

    assert payload["direction_aliases"]["UP"] == "LONG"
    assert payload["direction_aliases"]["DOWN"] == "SHORT"

    assert payload["field_aliases"]["sample_count"] == [
        "sample_count",
        "samples",
        "n",
    ]

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
