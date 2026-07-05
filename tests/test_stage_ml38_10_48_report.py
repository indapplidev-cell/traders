from pathlib import Path


REPORT = Path("reports/stage_ml38_10_48_read_only_test_only_mask_outcome_audit_report.md")


def test_stage_report_contains_ml38_10_48_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()

    assert "ml38.10.48" in text
    for required in (
        "42 pass / 931 removed",
        "only the 42 final pass rows",
        "full 6481 prediction stream was not found",
        "full 6481 cascade and outcome audit are not allowed",
        "not a production-like recompute",
        "not a tradable edge",
        "runtime and training were not run",
        "clean/fast/quick/sequence/full commands were not run",
        "no database writes",
        "ml_labels was not written",
        "ml_labels.direction_label was not substituted as predicted_label",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    ):
        assert required in text
