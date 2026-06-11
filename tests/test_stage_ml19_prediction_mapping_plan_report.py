from pathlib import Path


def test_stage_ml19_prediction_mapping_plan_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml19_prediction_mapping_plan_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML19",
        "Prediction Payload Mapping Plan",
        "gate_policy_prediction_payload_mapping",
        "ml19.1",
        "app/gates/gate_policy_prediction_mapping_plan.py",
        "app/gates/gate_policy_prediction_mapping_plan_reporter.py",
        "gate-policy-prediction-mapping-plan-preview",
        "gate-policy-prediction-mapping-plan-export",
        "reports/gate_policy_prediction_mapping_plan_summary.json",
        "runtime artifact",
        "runtime_adapter_implemented: false",
        "prob_up",
        "prob_down",
        "prob_flat",
        "direction",
        "LONG",
        "SHORT",
        "FLAT",
        "NONE",
        "confidence",
        "tp_before_sl_probability",
        "risk_score",
        "expected_move_atr",
        "model_version",
        "symbol",
        "interval",
        "regime",
        "market_regime",
        "detected_regime",
        "optional_target_count: 5",
        "optional_target_fields: risk_score, expected_move_atr, model_version, symbol, interval",
        "probability_argmax",
        "direct_float",
        "alias_first_present",
        "metadata_traceability",
        "does not implement the runtime adapter yet",
        "does not",
        "prediction_service.py",
        "predictor.py",
        "203 passed",
        "Stage ML20.1",
        "Prediction Runtime Adapter Contract",
    ]

    for phrase in required_phrases:
        assert phrase in text
