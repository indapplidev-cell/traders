from pathlib import Path


def test_stage_ml36_2_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml36_2_real_quality_validation_gate_summary_report.md")
    text = path.read_text(encoding="utf-8")

    assert "model_quality_validation failed with 'NoneType' object is not iterable" in text
    assert "Critical gap gate did not reach final failed_gates" in text
    assert "Candidate became FAILED instead of REJECTED" in text
    assert "Top-level regime summary contradicted candidate runtime status" in text
    assert "Regression tests" in text
    assert "ML38/candle/TA features: no" in text
