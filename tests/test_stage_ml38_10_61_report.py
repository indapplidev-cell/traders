from pathlib import Path


REPORT = Path(
    "reports/stage_ml38_10_61_solusdt_quick_quality_execution_harness_readiness_report.md"
)


def test_stage_report_contains_required_scope_and_decision() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.61",
        "Variant A",
        "no-run harness",
        "quick-quality was not run",
        "separate approval is required",
        "run_solusdt_quick_quality_once.py",
        "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT",
        "SOLUSDT_QUICK_QUALITY_EXECUTION_HARNESS_READY_NO_RUN",
        "ML38.10.62",
    ):
        assert phrase in text


def test_stage_report_contains_required_sections() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for heading in (
        "Why ML38.10.61 follows ML38.10.60",
        "Wrapper file",
        "Exact future command",
        "Dry-run behavior",
        "Execute-mode safety",
        "External logging contract",
        "Exit-code contract",
        "Command scope guardrails",
        "Real artifact guardrails",
        "Safety prohibitions",
        "Tests run",
        "Final decision",
    ):
        assert heading in text
