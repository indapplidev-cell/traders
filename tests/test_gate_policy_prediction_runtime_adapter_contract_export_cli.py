import json
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import (
    cli,
    export_gate_policy_runtime_adapter_contract_summary_report,
)


EXPECTED_REQUIRED_NUMERIC_FIELDS = [
    "prob_up",
    "prob_down",
    "prob_flat",
    "confidence",
    "tp_before_sl_probability",
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


def test_export_gate_policy_runtime_adapter_contract_summary_report_writes_json_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "gate_policy_runtime_adapter_contract_summary.json"

    result = export_gate_policy_runtime_adapter_contract_summary_report(
        output_path=output_path,
    )

    assert result == {
        "status": "ok",
        "output_path": str(output_path),
        "contract_name": "gate_policy_prediction_runtime_adapter_contract",
        "contract_version": "ml20.1",
        "required_numeric_count": 5,
        "required_context_count": 1,
        "optional_numeric_count": 2,
        "traceability_count": 3,
        "future_gate_policy_target_count": 9,
        "runtime_adapter_implemented": False,
    }

    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert payload["contract_version"] == "ml20.1"

    assert payload["required_probability_count"] == 3
    assert payload["required_numeric_count"] == 5
    assert payload["required_numeric_count"] == len(payload["required_numeric_fields"])
    assert payload["required_context_count"] == 1
    assert payload["optional_numeric_count"] == 2
    assert payload["traceability_count"] == 3
    assert payload["future_gate_policy_target_count"] == 9

    assert payload["required_numeric_fields"] == EXPECTED_REQUIRED_NUMERIC_FIELDS
    assert payload["required_context_fields"] == ["regime"]
    assert payload["optional_numeric_fields"] == ["risk_score", "expected_move_atr"]
    assert payload["traceability_fields"] == ["model_version", "symbol", "interval"]
    assert payload["future_gate_policy_target_fields"] == EXPECTED_TARGET_FIELDS

    assert payload["runtime_adapter_implemented"] is False
    assert payload["integration_status"]["prediction_service_imported"] is False
    assert payload["integration_status"]["predictor_imported"] is False
    assert payload["integration_status"]["database_connected"] is False
    assert payload["integration_status"]["model_inference_connected"] is False
    assert payload["integration_status"]["traders_core_connected"] is False
    assert payload["integration_status"]["live_trading_connected"] is False
    assert payload["integration_status"]["runtime_adapter_implemented"] is False

    assert "validation_policy" not in payload
    assert "required_probability_fields" not in payload
    assert "normalized_payload" not in payload
    assert "issues" not in payload
    assert "metadata" not in payload


def test_gate_policy_runtime_adapter_contract_export_cli_writes_json_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "cli_gate_policy_runtime_adapter_contract_summary.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-runtime-adapter-contract-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert output_path.exists()

    command_payload = json.loads(result.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert command_payload == {
        "status": "ok",
        "output_path": str(output_path),
        "contract_name": "gate_policy_prediction_runtime_adapter_contract",
        "contract_version": "ml20.1",
        "required_numeric_count": 5,
        "required_context_count": 1,
        "optional_numeric_count": 2,
        "traceability_count": 3,
        "future_gate_policy_target_count": 9,
        "runtime_adapter_implemented": False,
    }

    assert file_payload["contract_name"] == "gate_policy_prediction_runtime_adapter_contract"
    assert file_payload["contract_version"] == "ml20.1"

    assert file_payload["required_numeric_count"] == 5
    assert file_payload["required_numeric_count"] == len(
        file_payload["required_numeric_fields"]
    )
    assert file_payload["required_numeric_fields"] == EXPECTED_REQUIRED_NUMERIC_FIELDS

    assert file_payload["future_gate_policy_target_count"] == 9
    assert file_payload["future_gate_policy_target_fields"] == EXPECTED_TARGET_FIELDS

    assert file_payload["runtime_adapter_implemented"] is False
    assert file_payload["integration_status"]["runtime_adapter_implemented"] is False

    assert "validation_policy" not in file_payload
    assert "required_probability_fields" not in file_payload
    assert "normalized_payload" not in file_payload
    assert "issues" not in file_payload
    assert "metadata" not in file_payload


def test_gate_policy_runtime_adapter_contract_export_cli_has_safe_integration_status(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "safe_contract_summary.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "gate-policy-runtime-adapter-contract-export",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["integration_status"] == {
        "prediction_service_imported": False,
        "predictor_imported": False,
        "database_connected": False,
        "model_inference_connected": False,
        "traders_core_connected": False,
        "live_trading_connected": False,
        "runtime_adapter_implemented": False,
    }
