from scripts.forensic_dynamic_rr_calibration import _best_causal_net_rr, _metrics, outcome_label


def test_timeout_uses_net_outcome_instead_of_becoming_automatic_loss():
    assert outcome_label({"baseline_outcome": "TIME_EXPIRED", "net_return_bps": 1}) == 1
    assert outcome_label({"baseline_outcome": "TIME_EXPIRED", "net_return_bps": -1}) == 0
    assert outcome_label({"baseline_outcome": "TIME_EXPIRED", "net_return_bps": None}) is None


def test_noncausal_or_unentered_outcomes_are_not_probability_labels():
    assert outcome_label({"baseline_outcome": "ENTRY_EXPIRED"}) is None
    assert outcome_label({"baseline_outcome": "PATH_CAPTURED_NO_BASELINE_GEOMETRY"}) is None


def test_calibration_metrics_are_deterministic():
    rows = [
        {"raw_p_win": .2, "actual_win": 0},
        {"raw_p_win": .8, "actual_win": 1},
    ]
    result = _metrics(rows, "raw_p_win")
    assert result["count"] == 2
    assert result["predicted_mean"] == .5
    assert result["observed_rate"] == .5
    assert abs(result["brier_score"] - .04) < 1e-12


def test_best_causal_net_rr_uses_only_causal_future_safe_targets():
    diagnostic = {
        "stop_distance_bps": 20, "effective_total_cost_bps": 10,
        "target_considerations": [
            {"causal": True, "future_safe": True, "directionally_valid": True,
             "target_distance_bps": 70},
            {"causal": False, "future_safe": True, "directionally_valid": True,
             "target_distance_bps": 200},
        ],
    }
    assert _best_causal_net_rr(diagnostic) == 2.0


def test_best_causal_net_rr_rejects_targets_below_cost():
    diagnostic = {
        "stop_distance_bps": 20, "effective_total_cost_bps": 10,
        "target_considerations": [
            {"causal": True, "future_safe": True, "directionally_valid": True,
             "target_distance_bps": 9},
        ],
    }
    assert _best_causal_net_rr(diagnostic) is None
