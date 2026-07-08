from pathlib import Path


REPORT = Path("reports/stage_ml38_10_72_compact_archive_size_cap_fix_report.md")


def test_stage_ml38_10_72_report_contract() -> None:
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    required = (
        "ML38.10.72",
        "COMPACT_PER_SYMBOL_STAGE_SIZE_CAP_EXCEEDED_AFTER_HARDENING",
        "836.80 MB",
        "350.00 MB",
        "FIELD_CONTRACT_AUDIT_PASSED",
        "ml38.10.69",
        "45 valid streams",
        "manifest-only compaction",
        "No rerun",
        "Existing ML38.10.71 real artifacts were not mutated",
        "h08 remains separate and was not fixed",
        "Cascade/outcome remains blocked",
        "No production-like recompute or tradable edge is claimed",
        "ML38.10.73",
        "COMPACT_ARCHIVE_SIZE_CAP_FIX_",
    )
    for marker in required:
        assert marker in text


def test_stage_report_records_no_artifact_mutation_or_archive_recovery() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "No archive recovery was performed" in text
    assert "No new real sidecars or ZIP were created" in text
    assert "No commit, planning update, or snapshot was performed" in text
