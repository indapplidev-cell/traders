from pathlib import Path


REPORT = Path(
    "reports/stage_ml38_10_63_typeerror_downstream_analyzer_root_cause_audit_report.md"
)


def test_report_contains_diagnostic_and_root_cause() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.63",
        "TypeError root cause diagnostic",
        "directional_side_walk_forward_stability.py",
        "dict.fromkeys",
        "ROOT_CAUSE_CONFIRMED_NESTED_WARNING_PAYLOAD_NOT_NORMALIZED",
    ):
        assert phrase in text


def test_report_records_no_fix_no_rerun_and_next_stage() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "TypeError was not fixed",
        "wrapper/quick-quality was not rerun",
        "Cascade/outcome remains blocked",
        "ML38.10.64",
    ):
        assert phrase in text
