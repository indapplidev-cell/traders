from pathlib import Path


REPORT = Path("reports/stage_ml38_10_47_read_only_test_only_mask_cascade_counts_report.md")


def test_stage_report_contains_ml38_10_47_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()

    assert "ml38.10.47" in text
    for required in (
        "test-only 973",
        "full 6481 prediction stream was not found",
        "full 6481 cascade is not allowed",
        "runtime training was not run",
        "clean/fast/quick/sequence/full commands were not run",
        "no database writes",
        "ml_labels was not written",
        "ml_labels.direction_label was not substituted as predicted_label",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
        "test-only counts are not a production-like recompute",
    ):
        assert required in text
