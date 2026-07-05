from app.diagnostics.label_grid_sensitivity_recompute import (
    build_per_row_production_mask_join_audit,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


SOURCE_COUNTS = {
    "candle_count": 7282,
    "feature_row_count": 6481,
    "candidate_training_rows": 4536,
    "candidate_validation_rows": 972,
    "candidate_test_rows": 973,
    "production_directional_count": 74,
    "production_label_row_count": None,
}


def _by_name(rows):
    return {row["mask_name"]: row for row in rows}


def test_discovery_board_contains_required_score_sources() -> None:
    rows = _by_name(build_per_row_production_mask_join_audit(source_counts=SOURCE_COUNTS)[
        "mask_source_discovery_board"
    ])

    assert "setup_quality_score" in rows
    assert "entry_path_quality_score" in rows
    assert "stop_pressure_risk_score" in rows
    assert rows["setup_quality_score"]["source_path_or_field"]


def test_missing_sources_are_explicit_and_require_extractors() -> None:
    audit = build_per_row_production_mask_join_audit(source_counts=SOURCE_COUNTS)
    joins = _by_name(audit["per_row_mask_join_board"])

    assert joins["setup_quality_score"]["status"] == "SOURCE_NOT_FOUND"
    assert joins["entry_path_quality_score"]["status"] == "SOURCE_NOT_FOUND"
    assert joins["stop_pressure_risk_score"]["status"] == "SOURCE_NOT_FOUND"
    assert all(row["status"] == "MISSING_PER_ROW_SOURCE" for row in audit["missing_per_row_sources"])
    assert "extract_setup_quality_score_by_timestamp" in audit["next_extractor_requirements"]


def test_synthetic_scores_count_sequential_cascade_with_inclusive_thresholds() -> None:
    rows = [
        {"setup_quality_score": 0.60, "entry_path_quality_score": 0.70, "stop_pressure_risk_score": 0.45},
        {"setup_quality_score": 0.59, "entry_path_quality_score": 0.90, "stop_pressure_risk_score": 0.10},
        {"setup_quality_score": 0.80, "entry_path_quality_score": 0.69, "stop_pressure_risk_score": 0.20},
        {"setup_quality_score": 0.70, "entry_path_quality_score": 0.80, "stop_pressure_risk_score": 0.46},
    ]
    audit = build_per_row_production_mask_join_audit(
        source_counts={**SOURCE_COUNTS, "feature_row_count": 4},
        feature_rows=rows,
    )
    cascade = _by_name(audit["mask_cascade_count_board"])

    assert cascade["feature_rows_start"]["remaining_count"] == 4
    assert cascade["after_setup_quality_score_gte_0_60"]["removed_count"] == 1
    assert cascade["after_setup_quality_score_gte_0_60"]["remaining_count"] == 3
    assert cascade["after_entry_path_quality_score_gte_0.70"]["removed_count"] == 1
    assert cascade["after_entry_path_quality_score_gte_0.70"]["remaining_count"] == 2
    assert cascade["after_stop_pressure_risk_score_lte_0_45"]["removed_count"] == 1
    assert cascade["after_stop_pressure_risk_score_lte_0_45"]["remaining_count"] == 1


def test_entry_threshold_071_is_taken_from_config_evidence() -> None:
    audit = build_per_row_production_mask_join_audit(
        source_counts={"feature_row_count": 2},
        feature_rows=[
            {"setup_quality_score": 1.0, "entry_path_quality_score": 0.70, "stop_pressure_risk_score": 0.0},
            {"setup_quality_score": 1.0, "entry_path_quality_score": 0.71, "stop_pressure_risk_score": 0.0},
        ],
        config_payload={"entry_path_quality_min_threshold": 0.71},
    )
    cascade = _by_name(audit["mask_cascade_count_board"])
    join = _by_name(audit["per_row_mask_join_board"])["entry_path_quality_score"]

    assert cascade["after_entry_path_quality_score_gte_0.71"]["remaining_count"] == 1
    assert join["threshold_applied"] == 0.71


def test_incomplete_join_keeps_sensitivity_board_not_actionable() -> None:
    audit = build_per_row_production_mask_join_audit(source_counts=SOURCE_COUNTS)

    assert "PER_ROW_MASK_JOIN_NOT_COMPLETE" in audit["production_mask_join_decision"]
    assert "SENSITIVITY_BOARD_REMAINS_NOT_ACTIONABLE" in audit["production_mask_join_decision"]
    assert "DO_NOT_CHANGE_LABELS_YET" in audit["production_mask_join_decision"]
    assert "DO_NOT_CHANGE_GATES" in audit["production_mask_join_decision"]
    assert "DO_NOT_RUN_TRAINING" in audit["production_mask_join_decision"]


def test_reporter_preserves_and_renders_ml38_10_42_block() -> None:
    audit = build_per_row_production_mask_join_audit(source_counts=SOURCE_COUNTS)
    payload = {
        "per_row_production_mask_join_audit": audit,
        "per_row_mask_join_board": audit["per_row_mask_join_board"],
        "missing_per_row_sources": audit["missing_per_row_sources"],
        "next_extractor_requirements": audit["next_extractor_requirements"],
        "production_mask_join_decision": audit["production_mask_join_decision"],
    }

    compact = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(payload)
    markdown = MultiSymbolFeatureRegimeReporter()._markdown(payload)

    assert compact["per_row_production_mask_join_audit"]["diagnostic_version"] == "ml38.10.42"
    assert "ML38.10.42 Per-row Production Mask Join Audit" in markdown

