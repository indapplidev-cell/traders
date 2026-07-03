from pathlib import Path


def test_stage_ml38_10_36_report_exists_and_documents_constraints() -> None:
    report = Path("reports/stage_ml38_10_36_threshold_flat_bias_audit_report.md")
    text = report.read_text(encoding="utf-8")

    for expected in (
        "ML38.10.36",
        "Threshold Sensitivity",
        "Flat-Bias Root-Cause",
        "No fast-debug",
        "No quick-quality",
        "No clean_traders_ml.py",
        "No auto-activation",
    ):
        assert expected in text
