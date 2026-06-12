from pathlib import Path


def test_stage_ml31_expanded_grid_validation_report_exists_and_mentions_scope() -> None:
    report_path = Path("reports/stage_ml31_expanded_grid_validation_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")
    required_phrases = [
        "Stage ML31",
        "expanded grid",
        "gap-aware",
        "anti-collapse",
        "candidate",
        "walk-forward",
        "profit-aware",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML32",
    ]

    for phrase in required_phrases:
        assert phrase in text
