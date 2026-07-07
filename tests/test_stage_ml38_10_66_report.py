from pathlib import Path


REPORT = Path("reports/stage_ml38_10_66_post_fix_solusdt_model_quality_triage_report.md")


def test_stage_report_exists_and_identifies_stage() -> None:
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "ML38.10.66" in text
    assert "Candidate status summary" in text
    assert "45 rejected" in text
    assert "1 failed" in text


def test_stage_report_records_next_action_and_guardrails() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "Selected next training/quality action" in text
    assert "CALIBRATION_TUNING" in text
    assert "ML38.10.67" in text
    assert "no rerun" in text.lower()
    assert "cascade/outcome blocked" in text.lower()
    assert "not tradable edge" in text.lower()
