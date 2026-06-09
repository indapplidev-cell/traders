from pathlib import Path


def test_stage_ml16_prediction_contract_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml16_prediction_contract_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML16",
        "Prediction Payload Contract",
        "gate_policy_prediction_payload",
        "ml16.1",
        "GatePolicyPredictionContractReporter",
        "gate-policy-prediction-contract-preview",
        "gate-policy-prediction-contract-export",
        "reports/gate_policy_prediction_contract_report.json",
        "runtime artifact",
        "regime",
        "direction",
        "confidence",
        "tp_before_sl_probability",
        "baseline_profit_factor",
        "sample_count",
        "149 passed",
        "does not integrate GatePolicy with live prediction services",
        "Stage ML17.1",
    ]

    for phrase in required_phrases:
        assert phrase in text
