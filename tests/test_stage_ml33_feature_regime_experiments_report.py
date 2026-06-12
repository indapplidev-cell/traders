from pathlib import Path


def test_stage_ml33_feature_regime_experiments_report_exists_and_mentions_scope() -> None:
    report_path = Path("reports/stage_ml33_feature_regime_experiments_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")
    required_phrases = [
        "Stage ML33",
        "feature/regime-aware",
        "feature diagnostics",
        "regime diagnostics",
        "feature leakage",
        "candidate",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML34",
    ]

    for phrase in required_phrases:
        assert phrase in text
