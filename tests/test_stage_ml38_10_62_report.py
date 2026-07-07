from pathlib import Path


REPORT = Path("reports/stage_ml38_10_62_real_solusdt_quick_quality_wrapper_execution_audit_report.md")


def test_report_contains_execution_and_sidecar_evidence() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.62", "explicitly approved", "run_solusdt_quick_quality_once.py",
        "python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT",
        "Wrapper exit code: `1`", "Child exit code: `1`", "45 complete sidecar sets",
        "EXACT_BYTE_VALID", "LF_ONLY_VALID", "ml38.10.58", "RUNTIME_TRUTH_VALID",
        "COMPLETION_EVIDENCE_VALID", "ARCHIVE_VALID", "NO_LABEL_SUBSTITUTION_DETECTED",
        "WRAPPER_EXECUTION_FAILED",
    ):
        assert phrase in text


def test_report_keeps_disallowed_claims_blocked() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "cascade/outcome was not run and remains blocked",
        "production-like recompute is not claimed",
        "tradable edge is not claimed",
        "No live trading or automatic activation occurred",
    ):
        assert phrase in text
