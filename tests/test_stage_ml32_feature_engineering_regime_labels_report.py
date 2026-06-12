from pathlib import Path


def test_stage_ml32_feature_engineering_regime_labels_report_exists_and_mentions_scope() -> None:
    report_path = Path("reports/stage_ml32_feature_engineering_regime_labels_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")
    required_phrases = [
        "Stage ML32",
        "feature engineering",
        "regime-specific labels",
        "feature leakage",
        "feature group quality",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML33",
    ]

    for phrase in required_phrases:
        assert phrase in text
