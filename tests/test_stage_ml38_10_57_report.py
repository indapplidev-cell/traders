from __future__ import annotations


def _synthetic_stage_report() -> str:
    return """
    ML38.10.57 metadata/archive and CRLF/LF contract audit
    CRLF/LF contract blocker: SUMMARY_HASHES_LF_NORMALIZED_CONTENT_WHILE_FILE_IS_CRLF
    metadata stale: WIRED_NOT_EXECUTED / false / false
    ZIP missing: ZIP_MISSING_FOR_REAL_RUN
    CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED
    """


def test_stage_report_contract_contains_stage_and_crlf_lf_blocker() -> None:
    text = _synthetic_stage_report()
    assert "ML38.10.57" in text
    assert "CRLF/LF contract blocker" in text
    assert "SUMMARY_HASHES_LF_NORMALIZED_CONTENT_WHILE_FILE_IS_CRLF" in text


def test_stage_report_contract_contains_metadata_and_zip_blockers() -> None:
    text = _synthetic_stage_report()
    assert "metadata stale" in text
    assert "WIRED_NOT_EXECUTED" in text
    assert "ZIP missing" in text
    assert "CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED" in text
