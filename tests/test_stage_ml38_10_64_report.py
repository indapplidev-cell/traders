from pathlib import Path


REPORT = Path(
    "reports/stage_ml38_10_64_typeerror_downstream_analyzer_minimal_fix_report.md"
)


def test_report_exists_and_identifies_fix_and_decision() -> None:
    assert REPORT.exists()
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.64",
        "TYPEERROR_MINIMAL_FIX_IMPLEMENTED_NO_RERUN_SYNTHETIC_TESTED",
        "app/diagnostics/directional_side_walk_forward_stability.py",
        "DirectionalSideWalkForwardStabilityAnalyzer._candidate_row",
        "dict.fromkeys",
        "walk_forward_stability_warnings",
        "Synthetic regression tests",
    ):
        assert phrase in text


def test_report_records_guardrails_and_next_stage() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "no wrapper/quick-quality rerun",
        "no real artifact mutation",
        "no labels/gates/model changes",
        "Cascade/outcome remains blocked",
        "not production-like recompute",
        "tradable edge is not claimed",
        "ML38.10.65",
    ):
        assert phrase in text
