from pathlib import Path


REPORT_PATH = Path("reports/stage_ml38_10_40_production_label_semantics_parity_audit_report.md")


def test_stage_report_documents_scope_tests_and_prohibitions() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")
    required = (
        "ML38.10.40", "ML38.10.39", "96", "TOO_NOISY", "FLAT about 92%",
        "production_label_semantics_parity_audit", "label_recompute_semantics_gap_board",
        "current_config_mapping_audit", "ml38_10_40_parity_decision",
        "test_ml38_10_40_production_label_semantics_parity_audit.py",
        "test_stage_ml38_10_40_report.py", "python -m py_compile", "python -m pytest",
        "runtime training was not run", "clean/fast/quick/sequence/full were not run",
        "database writes were not performed", "ml_labels were not written",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    )
    for item in required:
        assert item in text
