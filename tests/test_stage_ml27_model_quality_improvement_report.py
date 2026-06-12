from pathlib import Path


def test_stage_ml27_model_quality_improvement_report_exists_and_mentions_scope() -> None:
    report_path = Path("reports/stage_ml27_model_quality_improvement_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")

    required_phrases = [
        "Stage ML27",
        "Model Quality Improvement",
        "gaps",
        "79 gaps",
        "anti-collapse",
        "directional bias",
        "walk-forward stability",
        "profit-aware",
        "label grid",
        "candidate selector",
        "QUALITY_REJECTED",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML28",
    ]

    for phrase in required_phrases:
        assert phrase in text
