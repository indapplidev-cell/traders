from pathlib import Path


def test_stage_ml17_prediction_discovery_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml17_prediction_discovery_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML17",
        "Prediction Discovery Layer",
        "gate-policy-prediction-discovery-summary",
        "gate-policy-prediction-discovery-export",
        "reports/gate_policy_prediction_discovery_summary.json",
        "runtime artifact",
        "app/gates/gate_policy_prediction_discovery.py",
        "app/gates/gate_policy_prediction_discovery_reporter.py",
        "app/prediction/predictor.py",
        "app/prediction/prediction_service.py",
        "app/api/schemas.py",
        "app/evaluation/signal_gate_evaluator.py",
        "app/evaluation/profit_aware_evaluator.py",
        "app/diagnostics/prediction_probability_diagnostics.py",
        "prob_up",
        "prob_down",
        "prob_flat",
        "confidence",
        "risk_score",
        "expected_move_atr",
        "tp_before_sl_probability",
        "165 passed",
        "does not integrate GatePolicy with real prediction services",
        "Stage ML18.1",
    ]

    for phrase in required_phrases:
        assert phrase in text
