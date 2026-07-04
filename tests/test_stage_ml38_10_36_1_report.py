from pathlib import Path


def test_stage_ml38_10_36_1_report() -> None:
    report = Path(
        "reports/stage_ml38_10_36_1_compact_archive_size_hardening_report.md"
    )
    text = report.read_text(encoding="utf-8")

    for expected in (
        "ML38.10.36.1",
        "COMPACT_PER_SYMBOL_STAGE_SIZE_CAP_EXCEEDED",
        "compact_archive_pruner",
        "No model logic changes",
        "No gates softened",
        "No lv37",
    ):
        assert expected in text
