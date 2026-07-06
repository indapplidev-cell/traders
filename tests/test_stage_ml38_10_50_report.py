from pathlib import Path


REPORT = Path("reports/stage_ml38_10_50_full_dataset_prediction_sidecar_export_implementation_report.md")


def test_stage_report_contains_ml38_10_50_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()
    for required in (
        "ml38.10.50",
        "ml38.10.49 was design-only",
        "only synthetic tests",
        "real 6481 stream was not created",
        "quick-quality and training were not run",
        "separate user approval",
        "no database writes",
        "ml_labels and ml_predictions were not written",
        "labels, label builders, gates, and model logic were unchanged",
        "actual labels are forbidden as a prediction source",
        "full 6481 cascade/outcome remains prohibited",
        "no production-like recompute",
        "no tradable edge",
        "changed files",
        "added files",
        "tests run",
    ):
        assert required in text

