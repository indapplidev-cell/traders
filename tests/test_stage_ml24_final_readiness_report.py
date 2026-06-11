from pathlib import Path


def test_stage_ml24_final_readiness_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml24_final_standalone_readiness_audit_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML24",
        "Final standalone traders-ml readiness audit",
        "ML19",
        "ML20",
        "ML21",
        "ML22",
        "ML23",
        "/predict",
        "GatePolicy block",
        "replay/evaluation",
        "no orders",
        "no live",
        "no traders-core direct connection",
        "HTTP integration as future step",
    ]

    for phrase in required_phrases:
        assert phrase in text
