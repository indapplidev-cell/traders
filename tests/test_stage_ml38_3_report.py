from pathlib import Path


def test_stage_ml38_3_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml38_3_dataset_gap_repair_collapse_retuning_report.md")
    text = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML38.3",
        "Dataset Gap Repair",
        "Starting Point",
        "Gap Diagnostics",
        "Root Cause",
        "Fixes",
        "Tests",
        "Decision",
        "can proceed to ML38.4",
        "can proceed to ML39",
    ):
        assert expected in text
