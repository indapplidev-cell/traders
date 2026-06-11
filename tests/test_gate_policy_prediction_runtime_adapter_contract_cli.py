import json
import subprocess
import sys

from typer.testing import CliRunner

from app.cli.commands import (
    build_gate_policy_runtime_adapter_contract_preview_payload,
    cli,
)


EXPECTED_REQUIRED_NUMERIC_FIELDS = [
    "prob_up",
    "prob_down",
    "prob_flat",
    "confidence",
    "tp_before_sl_probability",
]

EXPECTED_TRACEABILITY_FIELDS = [
    "model_version",
    "symbol",
    "interval",
]

EXPECTED_TARGET_FIELDS = [
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


def test_build_gate_policy_runtime_adapter_contract_preview_payload() -> None:
    payload = build_gate_policy_runtime_adapter_contract_preview_payload()

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_probability_count"] == 3
    assert payload["required_numeric_count"] == 5
    assert payload["required_context_count"] == 1
    assert payload["optional_numeric_count"] == 2
    assert payload["traceability_count"] == 3
    assert payload["future_gate_policy_target_count"] == 9

    assert payload["required_numeric_fields"] == EXPECTED_REQUIRED_NUMERIC_FIELDS
    assert payload["required_context_fields"] == ["regime"]
    assert payload["optional_numeric_fields"] == ["risk_score", "expected_move_atr"]
    assert payload["traceability_fields"] == EXPECTED_TRACEABILITY_FIELDS
    assert payload["future_gate_policy_target_fields"] == EXPECTED_TARGET_FIELDS

    assert payload["runtime_adapter_implemented"] is False

    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_gate_policy_runtime_adapter_contract_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-runtime-adapter-contract-preview",
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_numeric_fields"] == EXPECTED_REQUIRED_NUMERIC_FIELDS
    assert payload["required_context_fields"] == ["regime"]
    assert payload["optional_numeric_fields"] == ["risk_score", "expected_move_atr"]
    assert payload["traceability_fields"] == EXPECTED_TRACEABILITY_FIELDS
    assert payload["future_gate_policy_target_fields"] == EXPECTED_TARGET_FIELDS

    assert payload["runtime_adapter_implemented"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False


def test_gate_policy_runtime_adapter_contract_preview_real_module_command_outputs_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli.commands",
            "gate-policy-runtime-adapter-contract-preview",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_numeric_count"] == 5
    assert payload["traceability_count"] == 3
    assert payload["future_gate_policy_target_count"] == 9

    assert payload["required_numeric_fields"] == EXPECTED_REQUIRED_NUMERIC_FIELDS
    assert payload["traceability_fields"] == EXPECTED_TRACEABILITY_FIELDS
    assert payload["future_gate_policy_target_fields"] == EXPECTED_TARGET_FIELDS

    assert payload["runtime_adapter_implemented"] is False
    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
