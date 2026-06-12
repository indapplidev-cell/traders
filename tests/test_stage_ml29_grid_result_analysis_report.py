from pathlib import Path


def test_stage_ml29_grid_result_analysis_report_contains_required_sections() -> None:
    report_path = Path("reports/stage_ml29_grid_result_analysis_report.md")

    assert report_path.exists()

    text = report_path.read_text(encoding="utf-8")
    required = [
        "Stage ML29",
        "analyzer",
        "reporter",
        "next experiment planner",
        "label-grid-results-analyze",
        "no live",
        "no orders",
        "no traders-core",
        "ML30",
    ]
    for item in required:
        assert item in text
