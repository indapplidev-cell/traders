from datetime import datetime, timezone

from app.diagnostics.evaluator_payload_reproduction import (
    build_evaluator_payload_source_audit,
    build_payload_reproduction_board,
    build_read_only_evaluator_payload_reproduction_audit,
    build_reproduced_mask_value_summary,
    classify_evaluator_payload_reproduction_decision,
    reproduce_entry_path_quality_score_read_only,
    reproduce_recovery_guard_decision_read_only,
    reproduce_stop_pressure_risk_score_read_only,
)


def _row() -> dict:
    return {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candle_open_time": datetime(2026, 4, 1, tzinfo=timezone.utc),
        "features_json": {
            "alt_trend_continuation_long_score": 0.85,
            "nison_expected_followthrough_score": 0.75,
            "schwager_invalidation_quality_score": 0.80,
            "path_16_chop_score": 0.10,
            "schwager_false_breakout_risk_score": 0.05,
        },
        "setup_quality_score": 0.82,
        "setup_expected_move_atr": 1.6,
        "setup_invalidation_distance_atr": 0.8,
        "predicted_label": "UP",
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [
            {"high": 100.2, "low": 99.05, "close": 99.10},
            {"high": 101.3, "low": 99.50, "close": 101.0},
        ],
    }


def _config() -> dict:
    return {
        "entry_path_quality_score_profile": "mae_aware_rr_v3",
        "entry_path_quality_min_threshold": 0.70,
        "stop_pressure_max_risk_score": 0.45,
        "take_profit_atr": 1.2,
        "stop_loss_atr": 1.4,
        "exit_timeout_bars": 9,
        "exit_mitigation_loss_r": 0.62,
        "exit_neutral_abs_r": 0.15,
    }


def test_source_audit_finds_all_three_in_memory_evaluator_sources() -> None:
    audit = build_evaluator_payload_source_audit(
        payload_rows=[_row()], candidate_config=_config()
    )

    functions = " ".join(audit["candidate_functions_or_classes"])
    required = audit["required_inputs"]
    assert "EntryPathQualityFilter.score_rows" in functions
    assert "entry_path_quality_score" in required
    assert "stop_pressure_risk_score" in required
    assert "recovery_guard_decision" in required
    assert audit["can_reproduce_entry_path_quality"] is True
    assert audit["can_reproduce_stop_pressure"] is True
    assert audit["can_reproduce_recovery_guard"] is True


def test_synthetic_inputs_reproduce_entry_path_and_stop_pressure_read_only() -> None:
    entry = reproduce_entry_path_quality_score_read_only([_row()], candidate_config=_config())
    stop = reproduce_stop_pressure_risk_score_read_only([_row()], candidate_config=_config())

    assert entry["status"] == "REPRODUCED_READ_ONLY"
    assert stop["status"] == "REPRODUCED_READ_ONLY"
    assert 0.0 <= entry["rows"][0]["entry_path_quality_score"] <= 1.0
    assert 0.0 <= stop["rows"][0]["stop_pressure_risk_score"] <= 1.0
    assert entry["requires_db_write"] is False
    assert stop["requires_training"] is False


def test_synthetic_recovery_inputs_reproduce_guard_decision_read_only() -> None:
    result = reproduce_recovery_guard_decision_read_only(
        [_row()], candidate_config=_config()
    )

    assert result["status"] == "REPRODUCED_READ_ONLY"
    assert result["rows"][0]["recovery_guard_decision"] is True
    assert result["rows"][0]["classic_result"] == "EXIT_MITIGATED"
    assert result["rows"][0]["guarded_result"] == "TP"


def test_missing_inputs_are_classified_without_crash() -> None:
    incomplete = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candle_open_time": datetime(2026, 4, 1, tzinfo=timezone.utc),
    }

    entry = reproduce_entry_path_quality_score_read_only([incomplete])
    stop = reproduce_stop_pressure_risk_score_read_only([incomplete])
    recovery = reproduce_recovery_guard_decision_read_only([incomplete])

    assert entry["status"] == "SOURCE_FOUND_INPUTS_MISSING"
    assert stop["status"] == "SOURCE_FOUND_INPUTS_MISSING"
    assert recovery["status"] == "SOURCE_FOUND_INPUTS_MISSING"
    assert entry["missing_inputs_by_row"][0]["missing_inputs"]


def test_summary_and_decision_block_cascade_when_one_value_is_missing() -> None:
    entry = reproduce_entry_path_quality_score_read_only([_row()], candidate_config=_config())
    stop = reproduce_stop_pressure_risk_score_read_only([_row()], candidate_config=_config())
    recovery = reproduce_recovery_guard_decision_read_only([_row()], candidate_config={})
    board = build_payload_reproduction_board(entry, stop, recovery, candidate_config=_config())
    summary = build_reproduced_mask_value_summary(board)
    decision = classify_evaluator_payload_reproduction_decision(summary)

    assert summary["can_continue_to_mask_cascade_counts"] is False
    assert "CANNOT_PROCEED_TO_MASK_CASCADE_COUNTS" in decision


def test_summary_and_decision_allow_cascade_when_all_values_reproduced() -> None:
    audit = build_read_only_evaluator_payload_reproduction_audit(
        payload_rows=[_row()], candidate_config=_config()
    )

    summary = audit["reproduced_mask_value_summary"]
    assert summary["reproduced_value_count"] == 3
    assert summary["can_continue_to_mask_cascade_counts"] is True
    assert "CAN_PROCEED_TO_MASK_CASCADE_COUNTS" in audit["decision"]
    assert audit["database_writes"] is False
    assert audit["ml_labels_writes"] is False
    assert audit["training_or_runtime_execution"] is False

