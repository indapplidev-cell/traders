from pathlib import Path


REPORT = Path("reports/stage_ml38_10_54_sidecar_quick_quality_wiring_implementation_report.md")


def test_stage_report_records_implementation_and_non_execution() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "ML38.10.54",
        "NOT_READY_SIDE",
        "WIRED_NOT_EXECUTED",
        "quick-quality was not run",
        "training/runtime was not run",
        "DB writes were not performed",
        "ml_labels/ml_predictions were not written",
        "real 6481 stream was not created",
        "full 6481 cascade/outcome remains prohibited",
        "no production-like recompute",
        "no tradable edge",
        "ML38.10.55",
    )
    for value in required:
        assert value in text


def test_stage_report_records_unchanged_behavior_and_overwrite_guard() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for value in (
        "labels/label builders/gates/model logic unchanged",
        "test-only 973",
        "source/config consistency",
        "overwrite guard",
        "reporter/analyzer metadata",
    ):
        assert value in text
