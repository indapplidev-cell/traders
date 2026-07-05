from pathlib import Path


REPORT = Path("reports/stage_ml38_10_49_read_only_full_dataset_prediction_payload_capture_design_report.md")


def test_stage_report_contains_ml38_10_49_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()

    assert "ml38.10.49" in text
    for required in (
        "ml38.10.48 showed only a test-only outcome on 42 rows",
        "profit_outcome_missing",
        "full 6481 predicted_label stream is missing",
        "design/read-only only",
        "capture/export implementation was not performed",
        "runtime and training were not run",
        "clean/fast/quick/sequence/full commands were not run",
        "no database writes",
        "ml_labels and ml_predictions were not written",
        "full 6481 cascade/outcome was not built",
        "not a production-like recompute",
        "not a tradable edge",
        "ml_labels.direction_label was not substituted as predicted_label",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    ):
        assert required in text
