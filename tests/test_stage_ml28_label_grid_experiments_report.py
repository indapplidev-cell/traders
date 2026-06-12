from pathlib import Path


def test_stage_ml28_label_grid_experiments_report_contains_required_sections() -> None:
    report_path = Path("reports/stage_ml28_label_grid_experiments_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")
    required = [
        "Stage ML28",
        "label grid experiments",
        "candidate ranking",
        "anti-collapse",
        "profit-aware",
        "walk-forward",
        "gap quality",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML29",
    ]
    for item in required:
        assert item in text
