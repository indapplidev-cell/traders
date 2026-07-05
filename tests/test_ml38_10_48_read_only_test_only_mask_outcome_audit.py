from datetime import datetime, timedelta, timezone

import pytest

from app.diagnostics.test_only_mask_outcome_audit import (
    build_final_pass_confusion_matrix,
    build_final_pass_directional_precision_board,
    build_final_pass_label_prediction_distribution,
    build_final_pass_probability_confidence_summary,
    build_final_pass_profit_outcome_summary,
    build_final_pass_sample_rows,
    build_full_dataset_guardrail,
    build_read_only_test_only_mask_outcome_audit,
    build_test_only_outcome_input_summary,
    build_test_only_outcome_interpretation,
)


def _row(index: int, predicted: str, actual: str, **overrides) -> dict:
    row = {
        "symbol": "SOLUSDT",
        "interval": "15m",
        "candle_open_time": datetime(2026, 4, 1, tzinfo=timezone.utc)
        + timedelta(minutes=15 * index),
        "predicted_label": predicted,
        "actual_label": actual,
        "direction_label": actual,
        "confidence": 0.50 + index / 100,
        "prob_up": 0.55,
        "prob_down": 0.25,
        "prob_flat": 0.20,
        "setup_quality_score": 0.80,
        "entry_path_quality_score": 0.75,
        "stop_pressure_risk_score": 0.20,
        "recovery_guard_decision": True,
    }
    row.update(overrides)
    return row


def _final_42() -> list[dict]:
    pairs = (
        [("UP", "UP")] * 5
        + [("UP", "DOWN")] * 3
        + [("UP", "FLAT")] * 12
        + [("DOWN", "DOWN")] * 5
        + [("DOWN", "UP")] * 4
        + [("DOWN", "FLAT")] * 13
    )
    return [_row(index, predicted, actual) for index, (predicted, actual) in enumerate(pairs)]


def test_input_summary_ready_for_42_complete_final_pass_rows() -> None:
    summary = build_test_only_outcome_input_summary(_final_42())

    assert summary["input_status"] == "TEST_ONLY_OUTCOME_INPUTS_READY"
    assert summary["final_pass_rows"] == 42
    assert summary["predicted_label_rows_available"] == 42
    assert summary["actual_label_rows_available"] == 42
    assert summary["duplicate_key_counts"] == {"final_pass_rows": 0}


def test_distribution_keeps_actual_and_predicted_separate() -> None:
    distribution = build_final_pass_label_prediction_distribution(_final_42())

    assert distribution["actual_label_distribution"] == {"DOWN": 8, "FLAT": 25, "UP": 9}
    assert distribution["predicted_label_distribution"] == {"DOWN": 22, "UP": 20}
    assert distribution["actual_directional_count"] == 17
    assert distribution["predicted_directional_count"] == 42


def test_confusion_matrix_counts_predicted_up_against_each_actual_label() -> None:
    confusion = build_final_pass_confusion_matrix(_final_42())

    assert confusion["matrix"]["UP"] == {"UP": 5, "DOWN": 3, "FLAT": 12}
    assert confusion["predicted_up_actual_up"] == 5
    assert confusion["predicted_up_actual_down"] == 3
    assert confusion["predicted_up_actual_flat"] == 12


def test_confusion_matrix_counts_predicted_down_against_each_actual_label() -> None:
    confusion = build_final_pass_confusion_matrix(_final_42())

    assert confusion["matrix"]["DOWN"] == {"UP": 4, "DOWN": 5, "FLAT": 13}
    assert confusion["predicted_down_actual_down"] == 5
    assert confusion["predicted_down_actual_up"] == 4
    assert confusion["predicted_down_actual_flat"] == 13


def test_actual_flat_is_leakage_and_not_a_directional_hit() -> None:
    confusion = build_final_pass_confusion_matrix(_final_42())

    assert confusion["correct_directional_predictions"] == 10
    assert confusion["wrong_directional_predictions"] == 7
    assert confusion["flat_leakage_count"] == 25
    assert confusion["flat_leakage_pct"] == pytest.approx(59.52381)


def test_directional_precision_board_computes_all_three_rates() -> None:
    board = build_final_pass_directional_precision_board(_final_42())
    by_side = {row["predicted_side"]: row for row in board}

    assert by_side["predicted_UP"]["precision_same_side"] == pytest.approx(5 / 20)
    assert by_side["predicted_UP"]["opposite_side_rate"] == pytest.approx(3 / 20)
    assert by_side["predicted_UP"]["flat_rate"] == pytest.approx(12 / 20)
    assert by_side["predicted_DOWN"]["precision_same_side"] == pytest.approx(5 / 22)
    assert by_side["all_predicted_directional"]["flat_rate"] == pytest.approx(25 / 42)


def test_probability_summary_computes_confidence_statistics() -> None:
    summary = build_final_pass_probability_confidence_summary(_final_42())

    assert summary["status"] == "PROBABILITY_FIELDS_AVAILABLE"
    assert summary["confidence_count"] == 42
    assert summary["confidence_min"] == pytest.approx(0.50)
    assert summary["confidence_max"] == pytest.approx(0.91)
    assert summary["confidence_mean"] == pytest.approx(0.705)
    assert summary["confidence_median"] == pytest.approx(0.705)
    assert summary["confidence_p25"] == pytest.approx(0.6025)
    assert summary["confidence_p75"] == pytest.approx(0.8075)


def test_probability_summary_reports_missing_fields_without_inference() -> None:
    rows = [{"predicted_label": "UP", "actual_label": "UP"}]
    summary = build_final_pass_probability_confidence_summary(rows)

    assert summary["status"] == "PROBABILITY_FIELDS_MISSING"
    assert set(summary["missing_fields"]) == {"confidence", "prob_up", "prob_down", "prob_flat"}


def test_profit_summary_does_not_invent_r_when_outcomes_are_absent() -> None:
    summary = build_final_pass_profit_outcome_summary(_final_42())

    assert summary["outcome_source_status"] == "PROFIT_OUTCOME_MISSING"
    assert summary["total_r"] is None
    assert summary["expectancy_r"] is None
    assert summary["profit_factor"] is None


def test_profit_summary_uses_explicit_net_r_only() -> None:
    rows = [
        _row(0, "UP", "UP", net_r=1.5),
        _row(1, "DOWN", "UP", net_r=-1.0),
        _row(2, "UP", "FLAT", net_r=0.0),
    ]
    summary = build_final_pass_profit_outcome_summary(rows)

    assert summary["outcome_source_status"] == "PROFIT_OUTCOME_AVAILABLE"
    assert summary["total_r"] == pytest.approx(0.5)
    assert summary["profit_factor"] == pytest.approx(1.5)
    assert summary["outcome_fields_used"] == ["net_r"]


def test_sample_rows_are_capped_at_ten() -> None:
    samples = build_final_pass_sample_rows(_final_42(), limit=100)

    assert len(samples) == 10
    assert set(samples[0]) >= {"candle_open_time", "predicted_label", "actual_label"}


def test_interpretation_never_claims_production_edge() -> None:
    interpretation = build_test_only_outcome_interpretation(sample_size=42)

    assert interpretation["sample_size_warning"] is True
    assert interpretation["production_like_recompute"] is False
    assert interpretation["production_ready_edge"] is False
    assert interpretation["can_infer_tradable_edge"] is False


def test_full_dataset_guardrail_forbids_6481_cascade_and_outcome_audit() -> None:
    guardrail = build_full_dataset_guardrail(final_test_pass_rows=42)

    assert guardrail["full_dataset_outcome_audit_allowed"] is False
    assert guardrail["full_dataset_cascade_allowed"] is False
    assert guardrail["actual_label_substitution_allowed"] is False
    assert "DO_NOT_BUILD_FULL_6481_CASCADE" in guardrail["decision"]


def test_audit_decision_contains_required_test_only_guardrails() -> None:
    audit = build_read_only_test_only_mask_outcome_audit(_final_42())

    assert "DO_NOT_TREAT_TEST_ONLY_OUTCOME_AS_TRADABLE_EDGE" in audit["decision"]
    assert "FULL_6481_CASCADE_NOT_ALLOWED" in audit["decision"]
    assert "DO_NOT_SUBSTITUTE_ACTUAL_LABEL_FOR_PREDICTION" in audit["decision"]
    assert "TEST_ONLY_OUTCOME_DIAGNOSTIC_COMPLETE" in audit["decision"]


def test_direction_label_is_never_used_as_prediction_fallback() -> None:
    row = _row(0, "UP", "DOWN")
    row.pop("predicted_label")
    summary = build_test_only_outcome_input_summary([row], expected_final_pass_rows=1)
    distribution = build_final_pass_label_prediction_distribution([row])

    assert summary["actual_label_rows_available"] == 1
    assert summary["predicted_label_rows_available"] == 0
    assert distribution["actual_label_distribution"] == {"DOWN": 1}
    assert distribution["predicted_label_distribution"] == {}
