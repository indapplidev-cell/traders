from datetime import datetime, timedelta, timezone

from app.diagnostics.test_only_evaluator_payload_reproduction import (
    build_full_dataset_guardrail,
    build_read_only_test_only_evaluator_payload_reproduction_audit,
    build_test_only_payload_reproduction_board,
    build_test_prediction_join_board,
    select_test_prediction_payload,
)


def _row(index: int = 0, **overrides) -> dict:
    row = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candle_open_time": datetime(2026, 4, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        "actual_label": "DOWN",
        "direction_label": "DOWN",
        "predicted_label": "UP",
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
        "market_regime": "TREND_UP",
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [
            {"high": 100.2, "low": 99.05, "close": 99.10},
            {"high": 101.3, "low": 99.50, "close": 101.0},
        ],
    }
    row.update(overrides)
    return row


def _config() -> dict:
    return {
        "entry_path_quality_score_profile": "mae_aware_rr_v3",
        "entry_path_quality_min_threshold": 0.71,
        "stop_pressure_max_risk_score": 0.45,
        "take_profit_atr": 1.2,
        "stop_loss_atr": 1.5,
        "exit_timeout_bars": 9,
        "exit_mitigation_loss_r": 0.45,
        "exit_neutral_abs_r": 0.15,
    }


def _payload(rows, selected_rows=None) -> dict:
    return {
        "calibrated_decision_diagnostics": {
            "calibrated_rows": rows,
            "selected_rows": rows if selected_rows is None else selected_rows,
        }
    }


def test_selects_calibrated_rows_with_timestamp_and_predicted_label() -> None:
    selected = select_test_prediction_payload(_payload([_row()]))

    assert selected["selected_payload_path"] == "calibrated_decision_diagnostics.calibrated_rows"
    assert selected["source_status"] == "TEST_TIMESTAMPED_PREDICTIONS_SELECTED"


def test_prefers_entry_path_original_prediction_over_predicted_label() -> None:
    calibrated = [_row(predicted_label="DOWN")]
    selected_rows = [_row(entry_path_original_predicted_label="UP", predicted_label="DOWN")]

    selected = select_test_prediction_payload(_payload(calibrated, selected_rows))

    assert selected["selected_payload_path"] == "calibrated_decision_diagnostics.selected_rows"
    assert selected["predicted_label_field"] == "entry_path_original_predicted_label"


def test_join_is_ready_for_973_matching_rows_and_never_full_dataset_ready() -> None:
    rows = [_row(index) for index in range(973)]

    join = build_test_prediction_join_board(rows, rows, rows)[0]

    assert join["join_status"] == "TEST_JOIN_READY"
    assert join["matched_feature_rows"] == 973
    assert join["matched_label_rows"] == 973
    assert join["full_dataset_rows_available"] is False


def test_reproduction_uses_prediction_payload_not_direction_label() -> None:
    # If direction_label were substituted, this row would not report predicted_label missing.
    row = _row()
    row.pop("predicted_label")

    board = build_test_only_payload_reproduction_board([row], candidate_config=_config())

    assert all(item["status"] == "SOURCE_FOUND_INPUTS_MISSING" for item in board)
    assert all("predicted_label" in item["missing_inputs"] for item in board)


def test_all_three_values_reproduce_on_complete_synthetic_row() -> None:
    board = build_test_only_payload_reproduction_board([_row()], candidate_config=_config())
    by_name = {item["value_name"]: item for item in board}

    assert by_name["entry_path_quality_score_by_timestamp"]["status"] == "REPRODUCED_READ_ONLY_TEST_ONLY"
    assert by_name["stop_pressure_risk_score_by_timestamp"]["status"] == "REPRODUCED_READ_ONLY_TEST_ONLY"
    assert by_name["recovery_guard_decision_by_timestamp"]["status"] == "REPRODUCED_READ_ONLY_TEST_ONLY"


def test_missing_predicted_label_is_classified_without_crash() -> None:
    row = _row()
    row.pop("predicted_label")

    audit = build_read_only_test_only_evaluator_payload_reproduction_audit(
        probability_payload=_payload([row]), candidate_config=_config()
    )

    assert audit["test_prediction_payload_source"]["source_status"] == "TEST_PREDICTIONS_MISSING_PREDICTED_LABEL"
    assert all(
        item["status"] == "SOURCE_FOUND_INPUTS_MISSING"
        for item in audit["test_only_payload_reproduction_board"]
    )


def test_full_dataset_guardrail_always_blocks_6481_cascade() -> None:
    guardrail = build_full_dataset_guardrail(test_only_ready=True)

    assert guardrail["full_dataset_cascade_allowed"] is False
    assert "DO_NOT_BUILD_FULL_6481_CASCADE" in guardrail["decision"]
    assert guardrail["actual_label_substitution_allowed"] is False


def test_decision_marks_test_only_ready_only_when_all_three_reproduced() -> None:
    ready = build_read_only_test_only_evaluator_payload_reproduction_audit(
        probability_payload=_payload([_row()]), candidate_config=_config()
    )
    incomplete_config = dict(_config())
    incomplete_config.pop("exit_mitigation_loss_r")
    blocked = build_read_only_test_only_evaluator_payload_reproduction_audit(
        probability_payload=_payload([_row()]), candidate_config=incomplete_config
    )

    assert "TEST_ONLY_MASK_CASCADE_COUNTS_READY" in ready["decision"]
    assert "TEST_ONLY_MASK_CASCADE_COUNTS_READY" not in blocked["decision"]
    assert "TEST_ONLY_MASK_CASCADE_COUNTS_NOT_READY" in blocked["decision"]


def test_full_6481_cascade_is_never_allowed_by_decision() -> None:
    audit = build_read_only_test_only_evaluator_payload_reproduction_audit(
        probability_payload=_payload([_row()]), candidate_config=_config()
    )

    assert "FULL_6481_CASCADE_NOT_ALLOWED" in audit["decision"]
    assert "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION" in audit["decision"]
    assert audit["test_only_cascade_readiness"]["can_build_full_6481_mask_cascade_counts"] is False
