from pathlib import Path


def test_stage_ml38_2_1_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml38_2_1_fresh_grid_orchestration_gap_gate_report.md")
    text = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML38.2.1",
        "What Was Broken",
        "What Was Fixed",
        "Files Changed",
        "Checks",
        "Fresh Grid / Archive Result",
        "Gate Consistency Result",
        "Decision",
        "ML38.2.1 technically completed",
        "fresh wrapper completed end-to-end",
        "manual archive assembly used",
        "model accepted",
        "can proceed to ML38.3",
        "can proceed to ML39",
    ):
        assert expected in text
