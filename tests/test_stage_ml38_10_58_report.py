from pathlib import Path


REPORT = Path("reports/stage_ml38_10_58_sidecar_writer_metadata_archive_contract_fix_report.md")


def test_stage_report_records_contract_fix_and_safety_boundaries() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for required in (
        "ML38.10.58",
        "CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED",
        "EXACT_BYTES_HASH_AND_SIZE_AFTER_WRITE",
        "sidecar_runtime_truth",
        "Archive/ZIP status contract",
        "Timeout/exit-code contract",
        "no quick-quality",
        "no database writes",
        "no existing real artifact mutation",
        "no production-like recompute claim",
        "no tradable-edge claim",
        "Full 6481 cascade/outcome remains prohibited",
    ):
        assert required in text


def test_stage_report_does_not_claim_full_pytest_or_archive_recovery() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "Full pytest is not authorized by this stage and was not run" in text
    assert "no archive recovery/ZIP creation" in text
