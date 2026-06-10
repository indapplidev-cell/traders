from pathlib import Path


def test_stage_ml18_prediction_runtime_shape_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml18_prediction_runtime_shape_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML18",
        "Prediction Runtime Shape Discovery",
        "gate-policy-prediction-runtime-shape-summary",
        "gate-policy-prediction-runtime-shape-export",
        "reports/gate_policy_prediction_runtime_shape_summary.json",
        "runtime artifact",
        "app/gates/gate_policy_prediction_runtime_shape.py",
        "app/gates/gate_policy_prediction_runtime_shape_reporter.py",
        "app/prediction/predictor.py",
        "app/prediction/prediction_service.py",
        "app/api/schemas.py",
        "tests/test_predictor.py",
        "tests/test_prediction_service.py",
        "tests/test_api_predict.py",
        "PredictionRuntime",
        "Predictor",
        "PredictionService",
        "PredictionResponse",
        "predict_from_feature_record",
        "prepare_runtime",
        "prob_up",
        "prob_down",
        "prob_flat",
        "confidence",
        "risk_score",
        "expected_move_atr",
        "tp_before_sl_probability",
        "model_version",
        "181 passed",
        "does not integrate GatePolicy with real prediction services",
        "Stage ML19.1",
    ]

    for phrase in required_phrases:
        assert phrase in text
