from app.diagnostics.label_grid_sensitivity_recompute import (
    build_production_denominator_mask_alignment_audit,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


CONFIG_ID = "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe"
SOURCE_COUNTS = {
    "candle_count": 7282,
    "feature_row_count": 6481,
    "candidate_training_rows": 4536,
    "candidate_validation_rows": 972,
    "candidate_test_rows": 973,
    "label_row_count": None,
}


def _audit():
    return build_production_denominator_mask_alignment_audit(
        source_counts=SOURCE_COUNTS,
        config_id=CONFIG_ID,
        config_payload={"entry_path_quality_min_threshold": 0.71},
        production_reference={"directional_count": 74},
        recompute_evidence={
            "directional_count": 6900,
            "sensitivity_board_actionable": False,
            "timeout_flat_semantics_aligned": False,
        },
    )


def _by_name(rows, key):
    return {row[key]: row for row in rows}


def test_mask_cascade_contains_required_production_alignment_steps() -> None:
    rows = _by_name(_audit()["mask_cascade_board"], "mask_name")

    assert "raw_candles" in rows
    assert "setup_quality_mask_sqmask060" in rows
    assert rows["setup_quality_mask_sqmask060"]["mapped_threshold"] == 0.60
    assert "entry_path_quality_epq070_or_071" in rows
    assert rows["entry_path_quality_epq070_or_071"]["mapped_threshold"] == 0.71
    assert "stop_pressure_sp045" in rows
    assert rows["stop_pressure_sp045"]["mapped_threshold"] == 0.45
    assert all(row["requires_db_write"] is False for row in rows.values())
    assert all(row["requires_label_builder_change"] is False for row in rows.values())


def test_denominator_board_records_candles_to_features_gap() -> None:
    gaps = _by_name(_audit()["denominator_gap_board"], "gap_name")
    row = gaps["candles_to_features_gap"]

    assert row["known_left_count"] == 7282
    assert row["known_right_count"] == 6481
    assert row["missing_count"] == 801


def test_split_rows_have_exact_feature_parity() -> None:
    gaps = _by_name(_audit()["denominator_gap_board"], "gap_name")
    row = gaps["features_to_training_dataset_gap"]

    assert row["known_right_count"] == 4536 + 972 + 973 == 6481
    assert row["missing_count"] == 0
    assert row["evidence"] == "SPLIT_PARITY_OK"


def test_missing_label_denominator_is_explicit() -> None:
    audit = _audit()
    gaps = _by_name(audit["denominator_gap_board"], "gap_name")

    assert gaps["production_label_count_missing"]["evidence"] == "NEEDS_PRODUCTION_LABEL_ROW_COUNT"
    assert "NEEDS_PRODUCTION_LABEL_ROW_COUNT" in audit["ml38_10_41_alignment_decision"]


def test_prerequisites_require_per_row_setup_quality() -> None:
    checklist = _audit()["production_like_recompute_prerequisite_checklist"]

    assert "PER_ROW_SETUP_QUALITY_REQUIRED" in checklist
    assert "PER_ROW_ENTRY_PATH_QUALITY_REQUIRED" in checklist
    assert "PER_ROW_STOP_PRESSURE_REQUIRED" in checklist
    assert "PRODUCTION_LABEL_DENOMINATOR_REQUIRED" in checklist


def test_current_evidence_keeps_sensitivity_board_not_actionable() -> None:
    decisions = _audit()["ml38_10_41_alignment_decision"]

    assert "DENOMINATOR_ALIGNMENT_NOT_COMPLETE" in decisions
    assert "MASK_CASCADE_NOT_FULLY_RECONSTRUCTED" in decisions
    assert "PRODUCTION_LIKE_RECOMPUTE_NOT_READY" in decisions
    assert "SENSITIVITY_BOARD_REMAINS_NOT_ACTIONABLE" in decisions
    assert "DO_NOT_CHANGE_LABELS_YET" in decisions


def test_reporter_preserves_and_renders_alignment_blocks() -> None:
    audit = _audit()
    payload = {
        "production_denominator_mask_alignment_audit": audit,
        "mask_cascade_board": audit["mask_cascade_board"],
        "denominator_gap_board": audit["denominator_gap_board"],
        "production_like_recompute_prerequisite_checklist": audit[
            "production_like_recompute_prerequisite_checklist"
        ],
        "ml38_10_41_alignment_decision": audit["ml38_10_41_alignment_decision"],
    }

    compact = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(payload)
    markdown = MultiSymbolFeatureRegimeReporter()._markdown(payload)

    assert compact["production_denominator_mask_alignment_audit"]["diagnostic_version"] == "ml38.10.41"
    assert compact["mask_cascade_board"]
    assert compact["denominator_gap_board"]
    assert "ML38.10.41 Production Denominator and Mask Alignment Audit" in markdown

