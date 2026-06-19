from app.diagnostics.decision_policy_grid import DecisionPolicyConfig, DecisionPolicyGrid


def test_decision_policy_grid_can_reduce_raw_up_collapse() -> None:
    rows = [
        {"prob_down": 0.34, "prob_flat": 0.30, "prob_up": 0.36},
        {"prob_down": 0.35, "prob_flat": 0.29, "prob_up": 0.36},
        {"prob_down": 0.32, "prob_flat": 0.34, "prob_up": 0.35},
        {"prob_down": 0.33, "prob_flat": 0.34, "prob_up": 0.35},
        {"prob_down": 0.39, "prob_flat": 0.28, "prob_up": 0.40},
        {"prob_down": 0.38, "prob_flat": 0.29, "prob_up": 0.39},
    ]
    actual = ["DOWN", "DOWN", "FLAT", "FLAT", "UP", "UP"]

    grid = DecisionPolicyGrid(
        configs=(
            DecisionPolicyConfig(policy_id="raw_argmax"),
            DecisionPolicyConfig(
                policy_id="balanced_offsets",
                down_offset=0.025,
                flat_offset=0.020,
                min_margin=0.015,
                ambiguous_to_flat=True,
                max_dominant_class_ratio=0.75,
                max_flat_ratio=0.50,
                min_up_ratio_when_actual_up_high=0.0,
            ),
        )
    )

    payload = grid.evaluate(
        probability_rows=rows,
        actual_labels=actual,
        baseline_accuracy=2 / 6,
    )

    assert payload["selected_policy_id"] == "balanced_offsets"
    assert payload["selected_policy"]["baseline_edge"] > 0
    assert payload["selected_policy"]["distribution_safe"] is True
    assert payload["selected_decision_source"] == "decision_policy_grid:balanced_offsets"


def test_decision_policy_grid_rejects_distribution_collapse() -> None:
    rows = [
        {"prob_down": 0.10, "prob_flat": 0.20, "prob_up": 0.70},
        {"prob_down": 0.11, "prob_flat": 0.20, "prob_up": 0.69},
        {"prob_down": 0.09, "prob_flat": 0.21, "prob_up": 0.70},
        {"prob_down": 0.10, "prob_flat": 0.20, "prob_up": 0.70},
    ]
    actual = ["DOWN", "DOWN", "FLAT", "UP"]

    grid = DecisionPolicyGrid(
        configs=(
            DecisionPolicyConfig(
                policy_id="raw_argmax",
                max_dominant_class_ratio=0.75,
                min_down_ratio_when_actual_down_high=0.20,
            ),
        )
    )

    payload = grid.evaluate(
        probability_rows=rows,
        actual_labels=actual,
        baseline_accuracy=0.5,
    )

    selected = payload["selected_policy"]
    assert selected["distribution_safe"] is False
    assert selected["distribution_rejection_reasons"]
