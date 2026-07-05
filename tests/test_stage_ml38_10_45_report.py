from pathlib import Path


REPORT = Path("reports/stage_ml38_10_45_read_only_predicted_label_payload_trace_report.md")


def test_stage_report_contains_ml38_10_45_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()

    assert "ml38.10.45" in text
    assert "predicted_label by timestamp" in text
    for required in (
        "runtime training was not run",
        "clean/fast/quick/sequence/full commands were not run",
        "no database writes",
        "ml_labels was not written",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
        "actual labels cannot be used as evaluator predicted direction",
    ):
        assert required in text

