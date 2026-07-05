from pathlib import Path


REPORT = Path("reports/stage_ml38_10_46_read_only_test_only_evaluator_payload_reproduction_report.md")


def test_stage_report_contains_ml38_10_46_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()

    assert "ml38.10.46" in text
    assert "test-only 973" in text
    assert "full 6481" in text
    for required in (
        "runtime training was not run",
        "clean/fast/quick/sequence/full commands were not run",
        "no database writes",
        "ml_labels was not written",
        "ml_labels.direction_label was not substituted as predicted_label",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
        "full 6481 cascade is not allowed",
    ):
        assert required in text
