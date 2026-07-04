from pathlib import Path


REPORT_PATH = Path(
    "reports/stage_ml38_10_36_2_compact_report_aggregation_consistency_report.md"
)


def test_stage_report_documents_scope_tests_and_safety() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")

    required = (
        "ML38.10.36.2",
        "compact report aggregation consistency",
        "aggregate_report_source_consistency",
        "compact_summary_source_used",
        "missing_fields_after_fallback",
        "source_priority_used",
        "multi_symbol_feature_regime_analyzer.py",
        "multi_symbol_feature_regime_reporter.py",
        "compact_archive_pruner.py",
        "test_ml38_10_36_2_compact_report_aggregation_consistency.py",
        "python -m py_compile",
        "python -m pytest",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "model logic, gates, labels, live trading, and auto-activation were not changed",
    )
    for item in required:
        assert item in text
