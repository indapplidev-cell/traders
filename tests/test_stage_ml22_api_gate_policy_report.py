from pathlib import Path


def test_stage_ml22_api_gate_policy_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml22_api_gate_policy_response_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML22",
        "API response with GatePolicy block",
        "/predict",
        "app/api/schemas.py",
        "app/api/gate_policy_response_builder.py",
        "app/api/routes_predict.py",
        "ML21 runtime binding",
        "gate_policy block",
        "old prediction fields are preserved",
        "traders-core",
        "live trading",
        "orders",
        "database was not changed",
        "Alembic was not touched",
        "ML23",
        "Replay / evaluation through GatePolicy",
    ]

    for phrase in required_phrases:
        assert phrase in text
