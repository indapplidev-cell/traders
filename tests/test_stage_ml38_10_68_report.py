from pathlib import Path


REPORT = Path("reports/stage_ml38_10_68_calibration_replay_field_contract_report.md")


def test_report_exists_and_contains_contract_evidence():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.68", "raw probabilities", "actual labels", "row alignment",
        "downstream policy output 472/109/392", "sidecar argmax 532/15/426",
        "best distribution-only policy 281/400/292", "must not be conflated",
        "h08 separate scope", "ML38.10.69",
    ):
        assert phrase.lower() in text.lower()


def test_report_contains_fail_closed_guardrails():
    text = REPORT.read_text(encoding="utf-8").lower()
    for phrase in (
        "no training run", "directional_confidence_floor 0.60 was not implemented",
        "flat override was not implemented", "cascade/outcome blocked",
        "production-like recompute", "tradable edge", "no artifact mutation",
    ):
        assert phrase.lower() in text

