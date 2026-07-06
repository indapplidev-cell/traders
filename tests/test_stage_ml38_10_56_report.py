from pathlib import Path


REPORT = Path("reports/stage_ml38_10_56_real_quick_quality_sidecar_validation_audit_report.md")


def test_stage_report_records_ml38_10_56_validation_results() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "ML38.10.56", "SOLUSDT", "15m", "exit code 124", "Python exit code",
        "45", "6481", "JSONL_INTEGRITY_FAILED", "SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED",
        "CONFIG_CONSISTENCY_CONFIRMED", "SIDECAR_METADATA_STALE_BUT_ARTIFACT_VALIDATION_PASSED",
        "ZIP_MISSING_FOR_REAL_RUN", "REAL_SIDECAR_STREAM_VALIDATION_FAILED",
    )
    for value in required:
        assert value in text


def test_stage_report_records_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "no cascade/outcome", "no production-like recompute", "no tradable edge",
        "no labels/gates/model changes", "no DB-mutating commands", "quick-quality was not run again",
    )
    for value in required:
        assert value in text
