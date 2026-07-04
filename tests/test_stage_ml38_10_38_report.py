from pathlib import Path


REPORT_PATH = Path(
    "reports/stage_ml38_10_38_label_threshold_horizon_sensitivity_audit_report.md"
)


def test_stage_report_documents_scope_tests_and_prohibitions() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")

    required = (
        "ML38.10.38",
        "FLAT about 92%",
        "directional_count about 74",
        "label_threshold_horizon_sensitivity_audit",
        "label_recoverability_requirements",
        "next_label_diagnostic_plan",
        "ml38_10_38_label_audit_decision",
        "test_ml38_10_38_label_threshold_horizon_sensitivity_audit.py",
        "test_stage_ml38_10_38_report.py",
        "python -m py_compile",
        "python -m pytest",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    )
    for item in required:
        assert item in text
