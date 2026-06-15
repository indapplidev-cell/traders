from pathlib import Path


def test_stage_ml38_4_1_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml38_4_1_parallel_run_id_ranking_wrapper_fix_report.md")
    text = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML38.4.1",
        "Parallel Run ID",
        "Failed Candidate Ranking",
        "Starting Point",
        "Root Cause",
        "Fixes",
        "Tests",
        "Decision",
        "can proceed to ML38.4 rerun",
        "can proceed to ML39",
        "duplicate key value violates unique constraint",
        "FAILED candidates are excluded",
    ):
        assert expected in text
