from pathlib import Path


REPORT_PATH = Path(
    "reports/stage_ml38_10_39_read_only_label_grid_sensitivity_recompute_report.md"
)


def test_stage_report_documents_scope_grid_tests_and_prohibitions() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")
    required = (
        "ML38.10.39",
        "ML38.10.38",
        "compact ZIP",
        "read-only in-memory recompute",
        "h8 / h12 / h16 / h24",
        "0.6/0.6",
        "0.10 / 0.20 / 0.30 / 0.40",
        "read_only_label_grid_sensitivity_recompute",
        "test_ml38_10_39_read_only_label_grid_sensitivity_recompute.py",
        "test_stage_ml38_10_39_report.py",
        "python -m py_compile",
        "python -m pytest",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "labels, label builders, gates, and model logic were not changed",
        "database was not changed and ml_labels were not written",
        "live trading and auto-activation were not changed",
    )
    for item in required:
        assert item in text
