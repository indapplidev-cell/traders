from datetime import datetime, timedelta, timezone

import pytest

from app.diagnostics.test_only_mask_cascade_counts import (
    build_full_dataset_guardrail,
    build_read_only_test_only_mask_cascade_counts_audit,
    build_test_only_distribution_before_after,
    build_test_only_final_mask_summary,
    build_test_only_mask_cascade_board,
    build_test_only_mask_input_summary,
    build_test_only_mask_removed_breakdown,
    classify_test_only_mask_cascade_decision,
)


def _row(index: int = 0, **overrides) -> dict:
    row = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candle_open_time": datetime(2026, 4, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        "setup_quality_score": 0.80,
        "entry_path_quality_score": 0.80,
        "stop_pressure_risk_score": 0.20,
        "recovery_guard_decision": True,
        "market_regime": "TREND_UP",
        "actual_label": "DOWN",
        "predicted_label": "UP",
    }
    row.update(overrides)
    return row


def test_input_summary_is_ready_when_all_973_streams_exist() -> None:
    summary = build_test_only_mask_input_summary([_row(index) for index in range(973)])

    assert summary["input_status"] == "TEST_ONLY_MASK_INPUTS_READY"
    assert summary["predicted_label_rows_available"] == 973
    assert summary["duplicate_key_counts"] == {"test_rows": 0}


def test_cascade_order_is_setup_entry_stop_recovery() -> None:
    board = build_test_only_mask_cascade_board([_row()])

    assert [row["step_name"] for row in board] == [
        "initial_test_rows",
        "setup_quality_mask",
        "entry_path_quality_mask",
        "stop_pressure_mask",
        "recovery_guard_mask",
        "final_test_mask_pass_rows",
    ]


def test_cascade_does_not_double_count_removed_rows() -> None:
    rows = [
        _row(0, setup_quality_score=0.59),
        _row(1, entry_path_quality_score=0.70),
        _row(2, stop_pressure_risk_score=0.46),
        _row(3, recovery_guard_decision=False),
        _row(4),
    ]
    breakdown = build_test_only_mask_removed_breakdown(build_test_only_mask_cascade_board(rows))

    assert breakdown["total_removed"] == 4
    assert breakdown["final_remaining"] == 1
    assert breakdown["no_double_counting"] is True


def test_setup_quality_threshold_060_is_inclusive() -> None:
    board = build_test_only_mask_cascade_board([
        _row(0, setup_quality_score=0.60),
        _row(1, setup_quality_score=0.5999),
    ])

    setup = next(row for row in board if row["step_name"] == "setup_quality_mask")
    assert setup["passed_rows"] == 1
    assert setup["removed_rows"] == 1


def test_entry_path_quality_threshold_071_is_inclusive() -> None:
    board = build_test_only_mask_cascade_board([
        _row(0, entry_path_quality_score=0.71),
        _row(1, entry_path_quality_score=0.7099),
    ])

    entry = next(row for row in board if row["step_name"] == "entry_path_quality_mask")
    assert entry["passed_rows"] == 1
    assert entry["removed_rows"] == 1


def test_stop_pressure_threshold_045_is_inclusive() -> None:
    board = build_test_only_mask_cascade_board([
        _row(0, stop_pressure_risk_score=0.45),
        _row(1, stop_pressure_risk_score=0.4501),
    ])

    stop = next(row for row in board if row["step_name"] == "stop_pressure_mask")
    assert stop["passed_rows"] == 1
    assert stop["removed_rows"] == 1


def test_recovery_guard_removes_only_blocked_or_failed_rows() -> None:
    board = build_test_only_mask_cascade_board([
        _row(0, recovery_guard_decision=True),
        _row(1, recovery_guard_decision=False),
        _row(2, recovery_guard_decision="PASSED"),
        _row(3, recovery_guard_decision="BLOCKED"),
    ])

    recovery = next(row for row in board if row["step_name"] == "recovery_guard_mask")
    assert recovery["passed_rows"] == 2
    assert recovery["removed_rows"] == 2


def test_final_summary_computes_rows_and_percentages() -> None:
    board = build_test_only_mask_cascade_board([
        _row(0), _row(1, setup_quality_score=0.10), _row(2, recovery_guard_decision=False), _row(3)
    ])
    summary = build_test_only_final_mask_summary(board)

    assert summary["final_pass_rows"] == 2
    assert summary["final_removed_rows"] == 2
    assert summary["final_pass_pct"] == pytest.approx(50.0)
    assert summary["final_removed_pct"] == pytest.approx(50.0)


def test_distributions_keep_actual_and_predicted_labels_separate() -> None:
    distributions = build_test_only_distribution_before_after([
        _row(0, actual_label="DOWN", predicted_label="UP"),
        _row(1, actual_label="FLAT", predicted_label="DOWN"),
    ])
    initial = distributions["initial_test_rows"]

    assert initial["actual_label_distribution"] == {"DOWN": 1, "FLAT": 1}
    assert initial["predicted_label_distribution"] == {"DOWN": 1, "UP": 1}
    assert initial["directional_actual_count"] == 1
    assert initial["flat_predicted_count"] == 0


def test_full_dataset_guardrail_always_forbids_full_cascade() -> None:
    for computed in (False, True):
        guardrail = build_full_dataset_guardrail(test_only_cascade_computed=computed)
        assert guardrail["full_dataset_cascade_allowed"] is False
        assert guardrail["actual_label_substitution_allowed"] is False
        assert "DO_NOT_BUILD_FULL_6481_CASCADE" in guardrail["decision"]


def test_decision_marks_counts_computed_only_after_success() -> None:
    ready_rows = [_row(index) for index in range(973)]
    ready_input = build_test_only_mask_input_summary(ready_rows)
    ready_final = build_test_only_final_mask_summary(build_test_only_mask_cascade_board(ready_rows))
    blocked_input = build_test_only_mask_input_summary(ready_rows[:-1])

    assert "TEST_ONLY_MASK_CASCADE_COUNTS_COMPUTED" in classify_test_only_mask_cascade_decision(ready_input, ready_final)
    assert "TEST_ONLY_MASK_CASCADE_COUNTS_COMPUTED" not in classify_test_only_mask_cascade_decision(blocked_input, ready_final)


def test_decision_always_preserves_test_only_and_full_dataset_guardrails() -> None:
    audit = build_read_only_test_only_mask_cascade_counts_audit([_row(index) for index in range(973)])

    assert "DO_NOT_TREAT_TEST_ONLY_COUNTS_AS_FULL_DATASET" in audit["decision"]
    assert "FULL_6481_CASCADE_NOT_ALLOWED" in audit["decision"]
    assert audit["full_dataset_guardrail"]["full_dataset_cascade_allowed"] is False


def test_direction_label_is_actual_only_and_never_prediction_fallback() -> None:
    row = _row()
    row.pop("actual_label")
    row.pop("predicted_label")
    row["direction_label"] = "DOWN"
    summary = build_test_only_mask_input_summary([row], expected_test_rows=1)
    distribution = build_test_only_distribution_before_after([row])["initial_test_rows"]

    assert summary["production_label_rows_available"] == 1
    assert summary["predicted_label_rows_available"] == 0
    assert distribution["actual_label_distribution"] == {"DOWN": 1}
    assert distribution["predicted_label_distribution"] == {}


def test_optional_explicit_regime_mask_is_applied_before_recovery() -> None:
    board = build_test_only_mask_cascade_board([
        _row(0, regime_context_eligible=True),
        _row(1, regime_context_eligible=False),
    ])
    names = [row["step_name"] for row in board]

    assert names.index("regime_context_mask") < names.index("recovery_guard_mask")
    regime = next(row for row in board if row["step_name"] == "regime_context_mask")
    assert regime["passed_rows"] == 1

