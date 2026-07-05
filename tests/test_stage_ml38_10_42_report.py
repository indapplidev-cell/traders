from pathlib import Path


def test_stage_ml38_10_42_report_documents_scope_and_prohibitions() -> None:
    path = Path("reports/stage_ml38_10_42_per_row_production_mask_join_audit_report.md")
    text = path.read_text(encoding="utf-8")

    required = (
        "ML38.10.42",
        "per_row_production_mask_join_audit",
        "split parity",
        "runtime training was not run",
        "clean/fast/quick/sequence/full were not run",
        "DB writes were not performed",
        "ml_labels was not written",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    )
    for phrase in required:
        assert phrase.lower() in text.lower()

