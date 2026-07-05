from pathlib import Path


REPORT = Path("reports/stage_ml38_10_44_read_only_evaluator_payload_reproduction_report.md")


def test_stage_report_documents_ml38_10_44_and_safety_constraints() -> None:
    text = REPORT.read_text(encoding="utf-8")

    assert "ML38.10.44" in text
    assert "read-only evaluator payload reproduction" in text.lower()
    for required in (
        "runtime training was not run",
        "clean/fast/quick/sequence/full commands were not run",
        "no database writes",
        "ml_labels was not written",
        "labels, label builders, gates, and model logic were not changed",
        "live trading and auto-activation were not changed",
    ):
        assert required in text.lower()
