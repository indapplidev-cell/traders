from pathlib import Path


REPORT_PATH = Path(
    "reports/stage_ml38_10_41_production_denominator_mask_alignment_audit_report.md"
)


def test_stage_report_documents_scope_findings_tests_and_prohibitions() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")
    required = (
        "ML38.10.41",
        "ML38.10.40",
        "ML38.10.39",
        "not actionable",
        "production_denominator_mask_alignment_audit",
        "mask_cascade_board",
        "denominator_gap_board",
        "production_like_recompute_prerequisite_checklist",
        "ml38_10_41_alignment_decision",
        "test_ml38_10_41_production_denominator_mask_alignment_audit.py",
        "test_stage_ml38_10_41_report.py",
        "python -m py_compile",
        "python -m pytest",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "database writes were not performed",
        "ml_labels were not written",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    )
    for item in required:
        assert item in text

