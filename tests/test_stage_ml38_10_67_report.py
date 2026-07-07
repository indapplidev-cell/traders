from pathlib import Path


REPORT = Path("reports/stage_ml38_10_67_solusdt_calibration_replay_report.md")


def test_stage_report_exists_and_records_required_evidence() -> None:
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "ML38.10.67" in text
    assert "CALIBRATION_TUNING" in text or "calibration replay" in text.lower()
    assert "actual FLAT 899" in text
    assert "predicted FLAT 109" in text
    assert "h08" in text
    assert "ML38.10.68" in text


def test_stage_report_records_fail_closed_guardrails() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()
    assert "no training run" in text
    assert "cascade/outcome blocked" in text
    assert "production-like recompute" in text
    assert "tradable edge" in text

