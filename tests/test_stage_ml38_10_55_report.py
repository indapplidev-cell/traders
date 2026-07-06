from pathlib import Path


REPORT = Path("reports/stage_ml38_10_55_post_wiring_preflight_probe_report.md")


def test_stage_report_records_ml38_10_55_results_and_readiness_gate() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "ML38.10.55",
        "WIRED_NOT_EXECUTED",
        "flag propagation",
        "TrainingService wiring",
        "row construction contract",
        "full-dataset boundary",
        "test-only rejection",
        "source/config consistency",
        "overwrite guard",
        "compact whitelist",
        "reporter/analyzer metadata",
        "import-cycle fix",
        "READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN",
    )
    for value in required:
        assert value in text


def test_stage_report_records_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "quick-quality was not run",
        "training/runtime was not run",
        "DB writes were not performed",
        "ml_labels/ml_predictions were not written",
        "real 6481 stream was not created",
        "full 6481 cascade/outcome remains prohibited",
        "no production-like recompute",
        "no tradable edge",
        "separate explicit user approval",
    )
    for value in required:
        assert value in text

