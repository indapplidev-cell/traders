from __future__ import annotations

from app.training.two_stage_thresholds import select_opportunity_threshold


def test_threshold_sweep_selects_passing_candidate_from_candidate_list() -> None:
    selection = select_opportunity_threshold(
        [0.52, 0.58, 0.66, 0.72, 0.81],
        [0, 1, 1, 0, 1],
        candidates=(0.50, 0.60, 0.70, 0.80),
        min_precision=0.50,
        min_recall=0.50,
        max_predicted_trade_rate=0.80,
        max_predicted_to_actual_trade_rate_ratio=3.0,
        max_false_positive_rate=0.50,
    )

    assert selection.selected_threshold in selection.threshold_candidates
    assert selection.to_dict()["threshold_candidates"] == [0.50, 0.60, 0.70, 0.80]
    assert selection.passed_precision_control is True


def test_threshold_sweep_still_selects_best_candidate_when_all_fail() -> None:
    selection = select_opportunity_threshold(
        [0.91, 0.88, 0.84, 0.79],
        [0, 0, 1, 0],
        candidates=(0.50, 0.60, 0.70),
        min_precision=0.90,
        min_recall=0.80,
        max_predicted_trade_rate=0.20,
        max_predicted_to_actual_trade_rate_ratio=1.10,
        max_false_positive_rate=0.10,
    )

    assert selection.selected_threshold in selection.threshold_candidates
    assert selection.passed_precision_control is False
    assert selection.failed_reasons
