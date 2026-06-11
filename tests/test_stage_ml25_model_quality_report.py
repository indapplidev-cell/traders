from pathlib import Path


def test_stage_ml25_model_quality_report_exists_and_documents_scope() -> None:
    report_path = Path("reports/stage_ml25_model_training_quality_validation_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML25",
        "Model Training & Quality Validation",
        "baseline",
        "calibration",
        "profit-aware",
        "walk-forward",
        "GatePolicy replay",
        "sample mode",
        "long-history validation",
        "no live trading",
        "no orders",
        "no auto activation",
        "ML26",
    ]

    for phrase in required_phrases:
        assert phrase in text
