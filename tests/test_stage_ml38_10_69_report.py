from pathlib import Path


REPORT = Path("reports/stage_ml38_10_69_sidecar_field_contract_implementation_report.md")


def test_stage_report_contains_contract_and_source_path() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "ML38.10.69", "SIDECAR_FIELD_CONTRACT_IMPLEMENTATION", "raw probabilities",
        "calibrated probabilities", "actual label", "row_alignment_key",
        "prediction layers", "fail-closed validation",
        "TrainingService.train -> build_full_dataset_prediction_sidecar_rows -> write_prediction_sidecar_artifacts",
    ):
        assert phrase in text


def test_stage_report_preserves_guardrails() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for phrase in (
        "no training/wrapper/quick-quality run", "no DB writes", "no real artifacts mutated",
        "no new real sidecars/ZIP", "h08 fix not applied",
        "directional_confidence_floor 0.60 not implemented", "flat override not implemented",
        "cascade/outcome remains blocked", "production-like recompute/tradable edge not claimed",
    ):
        assert phrase in text

