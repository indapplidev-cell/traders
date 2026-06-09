import json

from app.gates.gate_policy_prediction_contract import (
    GatePolicyPredictionPayloadContract,
)
from app.gates.gate_policy_prediction_contract_reporter import (
    GatePolicyPredictionContractReporter,
)


def test_gate_policy_prediction_contract_reporter_builds_full_payload() -> None:
    reporter = GatePolicyPredictionContractReporter()

    payload = reporter.contract_to_dict()

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

    assert payload["direction_aliases"]["BUY"] == "LONG"
    assert payload["direction_aliases"]["SELL"] == "SHORT"
    assert "trend_up" in payload["known_regime_values"]

    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False


def test_gate_policy_prediction_contract_reporter_builds_summary_payload() -> None:
    reporter = GatePolicyPredictionContractReporter()

    payload = reporter.contract_summary_to_dict()

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["version"] == "ml16.1"
    assert payload["required_count"] == 4
    assert payload["optional_count"] == 7
    assert payload["all_field_count"] == 11
    assert payload["alias_field_count"] == 11
    assert payload["direction_alias_count"] == 10
    assert payload["known_regime_count"] == 8

    assert "required_fields" not in payload
    assert "optional_fields" not in payload
    assert "field_aliases" not in payload


def test_gate_policy_prediction_contract_reporter_supports_custom_contract() -> None:
    reporter = GatePolicyPredictionContractReporter()
    contract = GatePolicyPredictionPayloadContract(
        required_fields=("regime", "direction"),
        optional_fields=("confidence",),
        known_regime_values=("trend_up", "unknown"),
    )

    payload = reporter.contract_to_dict(contract)

    assert payload["required_count"] == 2
    assert payload["optional_count"] == 1
    assert payload["all_field_count"] == 3
    assert payload["required_fields"] == ["regime", "direction"]
    assert payload["optional_fields"] == ["confidence"]
    assert payload["known_regime_values"] == ["trend_up", "unknown"]


def test_gate_policy_prediction_contract_reporter_converts_full_payload_to_json() -> None:
    reporter = GatePolicyPredictionContractReporter()

    json_payload = reporter.contract_to_json()
    payload = json.loads(json_payload)

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["version"] == "ml16.1"
    assert payload["required_count"] == 4
    assert payload["optional_count"] == 7
    assert payload["direction_aliases"]["UP"] == "LONG"
    assert payload["field_aliases"]["sample_count"] == [
        "sample_count",
        "samples",
        "n",
    ]


def test_gate_policy_prediction_contract_reporter_converts_summary_to_json() -> None:
    reporter = GatePolicyPredictionContractReporter()

    json_payload = reporter.contract_summary_to_json()
    payload = json.loads(json_payload)

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["required_count"] == 4
    assert payload["optional_count"] == 7
    assert payload["integration_status"]["database_connected"] is False


def test_gate_policy_prediction_contract_reporter_supports_compact_json() -> None:
    reporter = GatePolicyPredictionContractReporter()

    json_payload = reporter.contract_to_json(indent=None)

    assert "\n" not in json_payload

    payload = json.loads(json_payload)

    assert payload["contract_name"] == "gate_policy_prediction_payload"
    assert payload["all_field_count"] == 11
