from pathlib import Path


REPORT = Path("reports/stage_ml38_10_51_sidecar_exporter_fixture_audit_report.md")


def test_stage_report_contains_ml38_10_51_and_all_safety_prohibitions() -> None:
    text = REPORT.read_text(encoding="utf-8").lower()
    for required in (
        "ml38.10.51",
        "ml38.10.50 implemented the exporter, validator, and compact whitelist",
        "fixture/dry-run only",
        "only in pytest tmp_path",
        "real 6481 stream was not created",
        "quick-quality, training, and runtime were not run",
        "clean, fast-debug, and sequence commands were not run",
        "no database writes",
        "ml_labels and ml_predictions were not written",
        "labels, label builders, gates, and model logic were unchanged",
        "actual labels and ml_labels.direction_label are forbidden as predictions",
        "compact whitelist was checked with fixture paths",
        "full 6481 cascade/outcome remains prohibited",
        "no production-like recompute",
        "no tradable edge",
        "changed files",
        "added files",
        "tests run",
    ):
        assert required in text
