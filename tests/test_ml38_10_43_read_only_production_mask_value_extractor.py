from datetime import datetime, timezone

from app.diagnostics.label_grid_sensitivity_recompute import (
    build_mask_value_availability_summary,
    build_mask_value_extraction_board,
    build_production_label_extraction_summary,
    build_read_only_production_mask_value_extractor_audit,
    build_timestamp_join_key_audit,
)
from app.experiments.multi_symbol_feature_regime_reporter import MultiSymbolFeatureRegimeReporter


def _by_name(rows):
    return {row["value_name"]: row for row in rows}


def _identity(index: int) -> dict:
    return {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candle_open_time": datetime(2026, 4, 1, 0, index * 15, tzinfo=timezone.utc),
    }


def test_timestamp_audit_prefers_scoped_candle_open_time() -> None:
    audit = build_timestamp_join_key_audit()

    assert audit["preferred_join_key"] == "symbol+interval+candle_open_time"
    assert audit["join_key_status"] == "READY"


def test_extraction_board_contains_required_timestamp_streams() -> None:
    board = _by_name(build_mask_value_extraction_board())

    assert "setup_quality_score_by_timestamp" in board
    assert "production_selected_label_by_timestamp" in board


def test_db_backed_source_with_rows_is_extracted_read_only() -> None:
    labels = [{**_identity(0), "setup_quality_score": 0.7, "direction_label": "UP"}]
    board = _by_name(build_mask_value_extraction_board(
        production_label_rows=labels, expected_row_count=1
    ))

    assert board["setup_quality_score_by_timestamp"]["extraction_status"] == "EXTRACTED_READ_ONLY"
    assert board["production_selected_label_by_timestamp"]["extraction_status"] == "EXTRACTED_READ_ONLY"
    assert board["setup_quality_score_by_timestamp"]["requires_db_write"] is False


def test_in_memory_only_and_aggregate_sources_are_classified() -> None:
    board = _by_name(build_mask_value_extraction_board(
        aggregate_sources={"bad_dates": {"row_count": 4}}
    ))

    assert board["entry_path_quality_score_by_timestamp"]["extraction_status"] == "SOURCE_FOUND_BUT_IN_MEMORY_ONLY"
    assert board["bad_dates_time_slice_probe_metadata"]["extraction_status"] == "AGGREGATE_ONLY_SOURCE"


def test_label_summary_counts_distribution_on_synthetic_rows() -> None:
    rows = [
        {**_identity(0), "direction_label": "UP", "setup_quality_score": 0.8},
        {**_identity(1), "direction_label": "UP", "setup_quality_score": 0.7},
        {**_identity(2), "direction_label": "DOWN", "setup_quality_score": 0.6},
        {**_identity(3), "direction_label": "FLAT", "setup_quality_score": 0.2},
    ]
    summary = build_production_label_extraction_summary(
        rows, label_version="lv31", horizon_candles=12
    )

    assert summary["direction_label_distribution"]["UP"] == {"count": 2, "pct": 50.0}
    assert summary["direction_label_distribution"]["DOWN"] == {"count": 1, "pct": 25.0}
    assert summary["direction_label_distribution"]["FLAT"] == {"count": 1, "pct": 25.0}
    assert summary["direction_label_distribution"]["directional"] == {"count": 3, "pct": 75.0}
    assert summary["extraction_status"] == "EXTRACTED_READ_ONLY"


def test_missing_label_filters_are_explicit() -> None:
    summary = build_production_label_extraction_summary([
        {**_identity(0), "direction_label": "UP"}
    ])

    assert summary["extraction_status"] == "LABEL_FILTER_INCOMPLETE"
    assert "missing_label_version_filter" in summary["blockers"]
    assert "missing_horizon_filter" in summary["blockers"]


def test_availability_and_decision_block_incomplete_cascade() -> None:
    feature = {
        **_identity(0),
        "features_json": {"market_regime": "TREND"},
    }
    label = {
        **_identity(0),
        "setup_quality_score": 0.75,
        "direction_label": "UP",
        "label_version": "lv31",
        "horizon_candles": 12,
    }
    board = build_mask_value_extraction_board(
        feature_rows=[feature], production_label_rows=[label], expected_row_count=1
    )
    summary = build_mask_value_availability_summary(board)
    audit = build_read_only_production_mask_value_extractor_audit(
        feature_rows=[feature],
        production_label_rows=[label],
        source_counts={"feature_row_count": 1},
        label_version="lv31",
        horizon_candles=12,
    )

    assert summary["can_build_mask_cascade_counts"] is False
    assert "CANNOT_PROCEED_TO_MASK_CASCADE_COUNTS" in audit["ml38_10_43_extractor_decision"]
    assert "NEEDS_EVALUATOR_PAYLOAD_REPRODUCTION" in audit["decision"]


def test_reporter_preserves_and_renders_ml38_10_43_block() -> None:
    audit = build_read_only_production_mask_value_extractor_audit()
    payload = {
        "read_only_production_mask_value_extractor_audit": audit,
        "mask_value_extraction_board": audit["mask_value_extraction_board"],
        "ml38_10_43_extractor_decision": audit["ml38_10_43_extractor_decision"],
    }

    reporter = MultiSymbolFeatureRegimeReporter()
    compact = reporter.compact_summary_to_dict(payload)
    markdown = reporter._markdown(payload)

    assert compact["read_only_production_mask_value_extractor_audit"]["diagnostic_version"] == "ml38.10.43"
    assert "ML38.10.43 Read-only Production Mask Value Extractor Audit" in markdown
