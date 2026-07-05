from pathlib import Path


def test_stage_ml38_10_43_report_documents_scope_and_prohibitions() -> None:
    text = Path(
        "reports/stage_ml38_10_43_read_only_production_mask_value_extractor_report.md"
    ).read_text(encoding="utf-8")

    required = (
        "ML38.10.43",
        "compact ZIP does not contain the complete 6,481-row stream",
        "read_only_production_mask_value_extractor_audit",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "DB writes were not performed",
        "ml_labels was not written",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    )
    for phrase in required:
        assert phrase.lower() in text.lower()

