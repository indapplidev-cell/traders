from pathlib import Path


REPORT = Path("reports/stage_ml38_10_60_real_quick_quality_rerun_readiness_plan_report.md")


def test_stage_report_contains_required_scope_and_decision() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.60",
        "no-run readiness plan",
        "quick-quality was not run",
        "separate approval is required",
        "REAL_QUICK_QUALITY_RERUN_READINESS_PLAN_CREATED_NO_RUN",
        "ML38.10.61",
    ):
        assert phrase in text


def test_stage_report_contains_required_sections() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for heading in (
        "Why ML38.10.60 follows ML38.10.59",
        "Previous fixture validation summary",
        "No-run scope",
        "Exact future command",
        "Execution runbook",
        "Timeout and exit-code capture plan",
        "Post-run sidecar validation plan",
        "Metadata truth validation plan",
        "Archive/ZIP validation plan",
        "Label substitution guardrail",
        "Real artifact guardrail",
        "Decision gate",
        "Safety prohibitions",
        "Tests run",
        "Final decision",
    ):
        assert heading in text
