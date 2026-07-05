from app.diagnostics.predicted_label_payload_trace import (
    build_actual_vs_predicted_guardrail,
    build_candidate_payload_omission_audit,
    build_predicted_label_source_discovery_board,
    build_prediction_row_locator_board,
    build_read_only_predicted_label_payload_trace_audit,
    build_timestamp_prediction_join_readiness,
    classify_predicted_label_trace_decision,
)


def _rows(count: int, *, label_field: str = "predicted_label", time_field: str = "candle_open_time") -> list[dict]:
    return [
        {
            "symbol": "SOLUSDT",
            "interval": "15m",
            time_field: f"2026-04-01T00:{index:04d}:00+00:00",
            label_field: "UP",
            "prob_up": 0.7,
        }
        for index in range(count)
    ]


def _compact_candidate() -> dict:
    marker = {
        "omitted": True,
        "original_count": 973,
        "original_type": "list",
        "reason": "compact_report_profile_heavy_payload",
    }
    return {
        "bounded_calibrated_decision_selection": {"selected_predictions": marker},
        "calibrated_decision_diagnostics": {
            "calibrated_rows": marker,
            "selected_rows": marker,
        },
        "entry_path_quality_filter_diagnostics": {"score_rows": marker},
    }


def test_discovery_board_marks_selected_predictions_omitted_by_compact_profile() -> None:
    board = build_predicted_label_source_discovery_board(candidate_result=_compact_candidate())
    row = next(
        item
        for item in board
        if item["source_name"]
        == "bounded_calibrated_decision_selection.selected_predictions"
    )

    assert row["status"] == "FOUND_OMITTED_BY_COMPACT_PROFILE"
    assert row["omitted_by_compact_profile"] is True
    assert row["row_count"] == 973


def test_discovery_board_detects_timestamped_predictions() -> None:
    board = build_predicted_label_source_discovery_board(
        [
            {
                "source_name": "synthetic_selected_predictions",
                "source_type": "synthetic",
                "source_path_or_table": "memory",
                "value": _rows(3),
            }
        ]
    )

    row = next(
        item for item in board
        if item["source_name"] == "synthetic_selected_predictions"
    )
    assert row["status"] == "FOUND_TIMESTAMPED_PREDICTIONS"
    assert row["usable_for_reproduction"] is True


def test_locator_finds_supported_predicted_label_and_timestamp_candidates() -> None:
    cases = (
        ("predicted_label", "candle_open_time"),
        ("predicted_class", "open_time"),
        ("decision_label", "timestamp"),
    )
    for label_field, timestamp_field in cases:
        board = build_prediction_row_locator_board(
            uncompressed_full_candidate_result=_rows(
                1, label_field=label_field, time_field=timestamp_field
            )
        )
        row = next(
            item
            for item in board
            if item["payload_name"] == "uncompressed_full_candidate_result"
        )
        assert label_field in row["predicted_label_field_candidates"]
        assert timestamp_field in row["timestamp_field_candidates"]


def test_join_readiness_is_dataset_ready_for_6481_timestamped_rows() -> None:
    board = build_prediction_row_locator_board(
        ml_predictions_db_rows=_rows(6481, label_field="direction")
    )

    readiness = build_timestamp_prediction_join_readiness(board)

    assert readiness["join_status"] == "DATASET_PREDICTION_JOIN_READY"
    assert readiness["can_join_dataset_predictions"] is True


def test_join_readiness_is_partial_test_only_for_973_timestamped_rows() -> None:
    board = build_prediction_row_locator_board(
        uncompressed_full_candidate_result={
            "calibrated_decision_diagnostics": {"calibrated_rows": _rows(973)}
        }
    )

    readiness = build_timestamp_prediction_join_readiness(board)

    assert readiness["join_status"] == "PARTIAL_TEST_ONLY_JOIN_READY"
    assert readiness["can_join_test_predictions"] is True
    assert readiness["can_join_dataset_predictions"] is False
    assert "973" in readiness["denominator_warning"]
    assert "6481" in readiness["denominator_warning"]


def test_join_readiness_blocks_when_no_prediction_rows_are_found() -> None:
    readiness = build_timestamp_prediction_join_readiness(
        build_prediction_row_locator_board({})
    )

    assert readiness["join_status"] == "JOIN_BLOCKED_NO_PREDICTED_LABEL_ROWS"


def test_actual_vs_predicted_guardrail_forbids_actual_label_substitution() -> None:
    guardrail = build_actual_vs_predicted_guardrail()

    assert guardrail["actual_label_field"] == "ml_labels.direction_label"
    assert guardrail["substitution_allowed"] is False
    assert guardrail["safe_fallback"] is None


def test_decision_always_forbids_actual_label_substitution() -> None:
    for row_count in (0, 973, 6481):
        board = build_prediction_row_locator_board(
            ml_predictions_db_rows=_rows(row_count, label_field="direction")
        )
        decision = classify_predicted_label_trace_decision(
            build_timestamp_prediction_join_readiness(board)
        )
        assert "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION" in decision


def test_decision_allows_reproduction_only_with_timestamped_predictions() -> None:
    ready = build_timestamp_prediction_join_readiness(
        build_prediction_row_locator_board(
            uncompressed_full_candidate_result=_rows(973)
        )
    )
    blocked = build_timestamp_prediction_join_readiness(
        build_prediction_row_locator_board({})
    )

    assert "CAN_PROCEED_TO_EVALUATOR_PAYLOAD_REPRODUCTION" in classify_predicted_label_trace_decision(ready)
    assert "CAN_PROCEED_TO_EVALUATOR_PAYLOAD_REPRODUCTION" not in classify_predicted_label_trace_decision(blocked)


def test_decision_blocks_mask_cascade_when_predictions_are_missing() -> None:
    audit = build_read_only_predicted_label_payload_trace_audit(
        candidate_result=_compact_candidate()
    )

    assert "CANNOT_PROCEED_TO_MASK_CASCADE_COUNTS" in audit["decision"]
    assert audit["database_writes"] is False
    assert audit["ml_labels_writes"] is False
    assert audit["training_or_runtime_execution"] is False


def test_omission_audit_highlights_entry_path_score_rows() -> None:
    audit = build_candidate_payload_omission_audit(_compact_candidate())
    row = next(
        item
        for item in audit["important_payload_paths"]
        if item["path"] == "entry_path_quality_filter_diagnostics.score_rows"
    )

    assert row["omitted"] is True
    assert row["original_count"] == 973
    assert row["is_missing_predicted_label_source"] is True
