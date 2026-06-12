from pathlib import Path


def test_stage_ml30_label_feature_improvements_report_exists_and_mentions_scope() -> None:
    report_path = Path("reports/stage_ml30_label_feature_improvements_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")
    required_phrases = [
        "Stage ML30",
        "Label Feature Improvements",
        "gap-aware",
        "feature quality",
        "anti-collapse",
        "candidate acceptance thresholds",
        "label quality grid",
        "selector explanations",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML31",
    ]

    for phrase in required_phrases:
        assert phrase in text
