from pathlib import Path


REPORT = Path("reports/stage_ml38_10_70_post_field_contract_solusdt_rerun_readiness_report.md")


def test_stage_report_contains_readiness_evidence() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.70", "field contract", "SOLUSDT",
        "python run_solusdt_quick_quality_once.py --execute --i-understand-this-runs-real-quick-quality",
        "separate approval", "h08 risk", "dirty worktree policy",
        "wrapper/quick-quality/training not executed",
        "READY_FOR_SEPARATELY_APPROVED_SOLUSDT_QUICK_QUALITY_RERUN",
        "ML38.10.71",
    ):
        assert phrase in text


def test_stage_report_preserves_all_no_run_guardrails() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "no commit/planning/snapshot", "cascade/outcome blocked",
        "production-like recompute/tradable edge blocked",
        "1160 passed, 0 skipped, 0 warnings", "6485 vs 6481", "delta +4",
    ):
        assert phrase in text
