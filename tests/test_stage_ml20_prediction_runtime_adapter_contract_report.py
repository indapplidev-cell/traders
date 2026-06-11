from pathlib import Path


def test_stage_ml20_prediction_runtime_adapter_contract_report_exists_and_documents_scope() -> None:
    report_path = Path(
        "reports/stage_ml20_prediction_runtime_adapter_contract_report.md"
    )

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML20",
        "Prediction Runtime Adapter Contract",
        "gate_policy_prediction_runtime_adapter_contract",
        "ml20.1",
        "app/gates/gate_policy_prediction_runtime_adapter_contract.py",
        "app/gates/gate_policy_prediction_runtime_adapter_contract_reporter.py",
        "gate-policy-runtime-adapter-contract-preview",
        "gate-policy-runtime-adapter-contract-export",
        "reports/gate_policy_runtime_adapter_contract_summary.json",
        "runtime artifact",
        "runtime_adapter_implemented: false",
        "prob_up",
        "prob_down",
        "prob_flat",
        "confidence",
        "tp_before_sl_probability",
        "risk_score",
        "expected_move_atr",
        "regime",
        "model_version",
        "symbol",
        "interval",
        "required_numeric_count: 5",
        "required_numeric_fields: prob_up, prob_down, prob_flat, confidence, tp_before_sl_probability",
        "missing_required_numeric_field",
        "invalid_numeric_field",
        "negative_probability",
        "missing_required_context_field",
        "normalize to `None`",
        "validation_policy",
        "normalized_payload",
        "issues",
        "metadata",
        "does not implement the real runtime adapter yet",
        "prediction_service.py",
        "predictor.py",
        "227 passed",
        "Stage ML21.1",
        "Prediction Runtime Adapter Skeleton",
    ]

    for phrase in required_phrases:
        assert phrase in text
