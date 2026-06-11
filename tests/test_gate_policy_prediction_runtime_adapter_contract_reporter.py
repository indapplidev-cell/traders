import json

from app.gates.gate_policy_prediction_runtime_adapter_contract_reporter import (
    GatePolicyPredictionRuntimeAdapterContractReporter,
    build_runtime_adapter_contract_report,
    build_runtime_adapter_contract_report_summary,
)


def test_runtime_adapter_contract_reporter_builds_full_contract_report() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    payload = reporter.contract_to_dict()

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_probability_count"] == 3
    assert payload["required_numeric_count"] == 5
    assert payload["required_context_count"] == 1
    assert payload["optional_numeric_count"] == 2
    assert payload["traceability_count"] == 3
    assert payload["future_gate_policy_target_count"] == 9

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

    assert payload["validation_policy"] == {
        "missing_required_numeric_field": "error",
        "invalid_numeric_field": "error",
        "negative_probability": "error",
        "missing_required_context_field": "error",
        "invalid_optional_numeric_field": "normalize_to_none",
    }

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_runtime_adapter_contract_reporter_builds_summary_report() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    payload = reporter.summary_to_dict()

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_probability_count"] == 3
    assert payload["required_numeric_count"] == 5
    assert payload["required_context_count"] == 1
    assert payload["optional_numeric_count"] == 2
    assert payload["traceability_count"] == 3
    assert payload["future_gate_policy_target_count"] == 9

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

    assert payload["runtime_adapter_implemented"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False

    assert "validation_policy" not in payload
    assert "required_probability_fields" not in payload


def test_runtime_adapter_contract_reporter_builds_validation_report_for_valid_payload() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    payload = reporter.validation_to_dict(
        {
            "prob_up": 0.55,
            "prob_down": 0.25,
            "prob_flat": 0.20,
            "confidence": 0.7,
            "tp_before_sl_probability": 0.63,
            "risk_score": 0.2,
            "expected_move_atr": 1.4,
            "regime": "trend_up",
            "model_version": "model_v1",
            "symbol": "BTCUSDT",
            "interval": "15m",
        }
    )

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"
    assert payload["is_valid"] is True
    assert payload["issue_count"] == 0
    assert payload["issues"] == []
    assert payload["runtime_adapter_implemented"] is False

    assert payload["normalized_payload"]["prob_up"] == 0.55
    assert payload["normalized_payload"]["prob_down"] == 0.25
    assert payload["normalized_payload"]["prob_flat"] == 0.20
    assert payload["normalized_payload"]["confidence"] == 0.7
    assert payload["normalized_payload"]["tp_before_sl_probability"] == 0.63
    assert payload["normalized_payload"]["risk_score"] == 0.2
    assert payload["normalized_payload"]["expected_move_atr"] == 1.4
    assert payload["normalized_payload"]["regime"] == "trend_up"

    assert payload["metadata"] == {
        "model_version": "model_v1",
        "symbol": "BTCUSDT",
        "interval": "15m",
    }


def test_runtime_adapter_contract_reporter_builds_validation_report_for_invalid_payload() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    payload = reporter.validation_to_dict(
        {
            "prob_up": -0.1,
            "prob_down": "bad",
            "prob_flat": 0.2,
            "confidence": True,
            "tp_before_sl_probability": 0.5,
            "regime": "",
        }
    )

    assert payload["is_valid"] is False
    assert payload["issue_count"] == 4
    assert payload["runtime_adapter_implemented"] is False

    issue_codes = {
        issue["field"]: issue["code"]
        for issue in payload["issues"]
    }

    assert issue_codes["prob_up"] == "negative_probability"
    assert issue_codes["prob_down"] == "invalid_numeric_field"
    assert issue_codes["confidence"] == "invalid_numeric_field"
    assert issue_codes["regime"] == "missing_required_context_field"


def test_runtime_adapter_contract_reporter_converts_contract_to_json() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    json_payload = reporter.contract_to_json()
    payload = json.loads(json_payload)

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"
    assert payload["required_numeric_count"] == 5
    assert payload["future_gate_policy_target_count"] == 9
    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_runtime_adapter_contract_reporter_converts_summary_to_json() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    json_payload = reporter.summary_to_json()
    payload = json.loads(json_payload)

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"
    assert payload["required_numeric_fields"] == [
        "prob_up",
        "prob_down",
        "prob_flat",
        "confidence",
        "tp_before_sl_probability",
    ]
    assert payload["runtime_adapter_implemented"] is False
    assert "validation_policy" not in payload


def test_runtime_adapter_contract_reporter_converts_validation_to_json() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    json_payload = reporter.validation_to_json(
        {
            "prob_up": 0.4,
            "prob_down": 0.3,
            "prob_flat": 0.3,
            "confidence": 0.5,
            "tp_before_sl_probability": 0.6,
            "regime": "range",
        }
    )
    payload = json.loads(json_payload)

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"
    assert payload["is_valid"] is True
    assert payload["issue_count"] == 0
    assert payload["runtime_adapter_implemented"] is False


def test_runtime_adapter_contract_reporter_supports_compact_json() -> None:
    reporter = GatePolicyPredictionRuntimeAdapterContractReporter()

    contract_json = reporter.contract_to_json(indent=None)
    summary_json = reporter.summary_to_json(indent=None)
    validation_json = reporter.validation_to_json(
        {
            "prob_up": 0.4,
            "prob_down": 0.3,
            "prob_flat": 0.3,
            "confidence": 0.5,
            "tp_before_sl_probability": 0.6,
            "regime": "range",
        },
        indent=None,
    )

    assert "\n" not in contract_json
    assert "\n" not in summary_json
    assert "\n" not in validation_json

    assert json.loads(contract_json)["contract_name"] == (
        "gate_policy_prediction_runtime_adapter_contract"
    )
    assert json.loads(summary_json)["contract_version"] == "ml20.1"
    assert json.loads(validation_json)["is_valid"] is True


def test_build_runtime_adapter_contract_report_helpers() -> None:
    full_payload = build_runtime_adapter_contract_report()
    summary_payload = build_runtime_adapter_contract_report_summary()

    assert full_payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert summary_payload["contract_name"] == (
        "gate_policy_prediction_runtime_adapter_contract"
    )

    assert full_payload["contract_version"] == "ml20.1"
    assert summary_payload["contract_version"] == "ml20.1"

    assert full_payload["required_numeric_count"] == 5
    assert summary_payload["required_numeric_count"] == 5

    assert full_payload["integration_status"]["runtime_adapter_implemented"] is False
    assert summary_payload["runtime_adapter_implemented"] is False
