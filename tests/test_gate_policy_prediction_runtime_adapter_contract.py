import json

from app.gates.gate_policy_prediction_runtime_adapter_contract import (
    CONTRACT_NAME,
    CONTRACT_VERSION,
    FUTURE_GATE_POLICY_TARGET_FIELDS,
    OPTIONAL_NUMERIC_FIELDS,
    REQUIRED_CONTEXT_FIELDS,
    REQUIRED_NUMERIC_FIELDS,
    REQUIRED_PROBABILITY_FIELDS,
    TRACEABILITY_FIELDS,
    RuntimeAdapterValidationIssue,
    build_runtime_adapter_contract_summary,
    validate_runtime_prediction_payload_contract,
)


def test_runtime_adapter_validation_issue_to_dict() -> None:
    issue = RuntimeAdapterValidationIssue(
        field="prob_up",
        code="missing_required_numeric_field",
        message="Missing prob_up.",
    )

    assert issue.to_dict() == {
        "field": "prob_up",
        "code": "missing_required_numeric_field",
        "message": "Missing prob_up.",
        "severity": "error",
    }


def test_runtime_adapter_contract_accepts_valid_payload() -> None:
    payload = {
        "prob_up": 0.61,
        "prob_down": 0.21,
        "prob_flat": 0.18,
        "confidence": 0.72,
        "tp_before_sl_probability": 0.64,
        "risk_score": 0.31,
        "expected_move_atr": 1.45,
        "regime": "trend_up",
        "model_version": "model_v1",
        "symbol": "BTCUSDT",
        "interval": "15m",
    }

    result = validate_runtime_prediction_payload_contract(payload)

    assert result.is_valid is True
    assert result.issues == ()
    assert result.runtime_adapter_implemented is False

    assert result.normalized_payload["prob_up"] == 0.61
    assert result.normalized_payload["prob_down"] == 0.21
    assert result.normalized_payload["prob_flat"] == 0.18
    assert result.normalized_payload["confidence"] == 0.72
    assert result.normalized_payload["tp_before_sl_probability"] == 0.64
    assert result.normalized_payload["risk_score"] == 0.31
    assert result.normalized_payload["expected_move_atr"] == 1.45
    assert result.normalized_payload["regime"] == "trend_up"

    assert result.metadata == {
        "model_version": "model_v1",
        "symbol": "BTCUSDT",
        "interval": "15m",
    }


def test_runtime_adapter_contract_rejects_missing_required_fields() -> None:
    result = validate_runtime_prediction_payload_contract({})

    payload = result.to_dict()

    assert payload["is_valid"] is False
    assert payload["issue_count"] == 6

    issue_codes = {
        issue["field"]: issue["code"]
        for issue in payload["issues"]
    }

    assert issue_codes == {
        "prob_up": "missing_required_numeric_field",
        "prob_down": "missing_required_numeric_field",
        "prob_flat": "missing_required_numeric_field",
        "confidence": "missing_required_numeric_field",
        "tp_before_sl_probability": "missing_required_numeric_field",
        "regime": "missing_required_context_field",
    }

    assert payload["runtime_adapter_implemented"] is False


def test_runtime_adapter_contract_rejects_invalid_numeric_fields() -> None:
    payload = {
        "prob_up": "bad",
        "prob_down": 0.2,
        "prob_flat": 0.1,
        "confidence": True,
        "tp_before_sl_probability": None,
        "regime": "range",
    }

    result = validate_runtime_prediction_payload_contract(payload)
    result_payload = result.to_dict()

    assert result_payload["is_valid"] is False

    issue_codes = {
        issue["field"]: issue["code"]
        for issue in result_payload["issues"]
    }

    assert issue_codes["prob_up"] == "invalid_numeric_field"
    assert issue_codes["confidence"] == "invalid_numeric_field"
    assert issue_codes["tp_before_sl_probability"] == "invalid_numeric_field"


def test_runtime_adapter_contract_rejects_negative_probabilities() -> None:
    payload = {
        "prob_up": -0.1,
        "prob_down": 0.2,
        "prob_flat": 0.9,
        "confidence": 0.7,
        "tp_before_sl_probability": 0.6,
        "regime": "trend_down",
    }

    result = validate_runtime_prediction_payload_contract(payload)
    result_payload = result.to_dict()

    assert result_payload["is_valid"] is False
    assert result_payload["issue_count"] == 1
    assert result_payload["issues"][0]["field"] == "prob_up"
    assert result_payload["issues"][0]["code"] == "negative_probability"


def test_runtime_adapter_contract_normalizes_optional_fields_to_none() -> None:
    payload = {
        "prob_up": 0.4,
        "prob_down": 0.3,
        "prob_flat": 0.3,
        "confidence": 0.5,
        "tp_before_sl_probability": 0.55,
        "risk_score": "bad",
        "expected_move_atr": None,
        "regime": "range",
    }

    result = validate_runtime_prediction_payload_contract(payload)

    assert result.is_valid is True
    assert result.normalized_payload["risk_score"] is None
    assert result.normalized_payload["expected_move_atr"] is None


def test_runtime_adapter_contract_result_to_dict_is_json_safe() -> None:
    payload = {
        "prob_up": 0.4,
        "prob_down": 0.3,
        "prob_flat": 0.3,
        "confidence": 0.5,
        "tp_before_sl_probability": 0.55,
        "regime": "range",
        "model_version": "model_v2",
        "symbol": "ETHUSDT",
        "interval": "1h",
    }

    result = validate_runtime_prediction_payload_contract(payload)
    result_payload = result.to_dict()

    assert result_payload["contract_name"] == CONTRACT_NAME
    assert result_payload["contract_version"] == CONTRACT_VERSION
    assert result_payload["is_valid"] is True
    assert result_payload["issue_count"] == 0
    assert result_payload["runtime_adapter_implemented"] is False

    assert result_payload["required_probability_fields"] == list(
        REQUIRED_PROBABILITY_FIELDS
    )
    assert result_payload["required_numeric_fields"] == list(REQUIRED_NUMERIC_FIELDS)
    assert result_payload["required_context_fields"] == list(REQUIRED_CONTEXT_FIELDS)
    assert result_payload["optional_numeric_fields"] == list(OPTIONAL_NUMERIC_FIELDS)
    assert result_payload["traceability_fields"] == list(TRACEABILITY_FIELDS)
    assert result_payload["future_gate_policy_target_fields"] == list(
        FUTURE_GATE_POLICY_TARGET_FIELDS
    )

    json.dumps(result_payload, ensure_ascii=False)


def test_build_runtime_adapter_contract_summary() -> None:
    payload = build_runtime_adapter_contract_summary()

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_probability_fields"] == [
        "prob_up",
        "prob_down",
        "prob_flat",
    ]

    assert payload["required_numeric_fields"] == [
        "prob_up",
        "prob_down",
        "prob_flat",
        "confidence",
        "tp_before_sl_probability",
    ]

    assert payload["required_context_fields"] == ["regime"]
    assert payload["optional_numeric_fields"] == ["risk_score", "expected_move_atr"]
    assert payload["traceability_fields"] == ["model_version", "symbol", "interval"]

    assert payload["future_gate_policy_target_fields"] == [
        "direction",
        "confidence",
        "tp_before_sl_probability",
        "regime",
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
    ]

    assert payload["required_probability_count"] == 3
    assert payload["required_numeric_count"] == 5
    assert payload["required_context_count"] == 1
    assert payload["optional_numeric_count"] == 2
    assert payload["traceability_count"] == 3
    assert payload["future_gate_policy_target_count"] == 9

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False
