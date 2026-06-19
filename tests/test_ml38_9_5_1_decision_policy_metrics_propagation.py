from app.diagnostics.decision_policy_grid import apply_selected_decision_policy_metrics


def test_selected_decision_policy_metrics_override_stale_top_level_metrics() -> None:
    candidate = {
        "config_id": "lv10_h12_thr06_tp12_sl12_dp",
        "model_accuracy": 0.24357656731757452,
        "accuracy": 0.24357656731757452,
        "baseline_accuracy": 0.39568345323741005,
        "baseline_edge": -0.15210688591983554,
        "baseline_edge_status": "NEGATIVE_EDGE",
        "predicted_class_distribution": {
            "DOWN": 0.0041109969167523125,
            "FLAT": 0.9958890030832477,
            "UP": 0.0,
        },
        "actual_class_distribution": {
            "DOWN": 0.3617677286742035,
            "FLAT": 0.24254881808838644,
            "UP": 0.39568345323741005,
        },
        "baseline_edge_diagnostics": {
            "accuracy": 0.24357656731757452,
            "baseline_accuracy": 0.39568345323741005,
            "baseline_edge": -0.15210688591983554,
            "baseline_edge_status": "NEGATIVE_EDGE",
            "baseline_edge_gate_min": 0.0,
            "baseline_edge_gate_failed": True,
        },
        "collapse_diagnostics_v2": {
            "predicted_distribution": {
                "DOWN": 0.0041109969167523125,
                "FLAT": 0.9958890030832477,
                "UP": 0.0,
            },
            "actual_distribution": {
                "DOWN": 0.3617677286742035,
                "FLAT": 0.24254881808838644,
                "UP": 0.39568345323741005,
            },
        },
        "decision_policy_grid_diagnostics": {
            "selected_decision_source": "decision_policy_grid:raw_argmax",
            "selected_policy_id": "raw_argmax",
            "selected_policy": {
                "policy_id": "raw_argmax",
                "accuracy": 0.38335046248715315,
                "baseline_accuracy": 0.39568345323741005,
                "baseline_edge": -0.0123329907502569,
                "baseline_edge_status": "NEGATIVE_EDGE",
                "distribution_safe": False,
                "dominant_class": "UP",
                "dominant_class_ratio": 0.9331963001027749,
                "distribution_rejection_reasons": [
                    "dominant_class_ratio>0.75:UP=0.9332",
                    "down_coverage_too_low:actual=0.3618,predicted=0.0668,min=0.1200",
                ],
                "predicted_ratios": {
                    "DOWN": 0.06680369989722508,
                    "FLAT": 0.0,
                    "UP": 0.9331963001027749,
                },
                "actual_ratios": {
                    "DOWN": 0.3617677286742035,
                    "FLAT": 0.24254881808838644,
                    "UP": 0.39568345323741005,
                },
            },
        },
    }

    updated = apply_selected_decision_policy_metrics(candidate)

    assert updated["prediction_decision_source"] == "decision_policy_grid:raw_argmax"
    assert updated["decision_policy_selected_policy_id"] == "raw_argmax"
    assert updated["model_accuracy"] == 0.38335046248715315
    assert updated["accuracy"] == 0.38335046248715315
    assert updated["baseline_edge"] == -0.0123329907502569
    assert updated["accuracy_edge"] == -0.0123329907502569
    assert updated["baseline_edge_diagnostics"]["accuracy"] == 0.38335046248715315
    assert updated["baseline_edge_diagnostics"]["baseline_edge"] == -0.0123329907502569
    assert updated["predicted_class_distribution"] == {
        "DOWN": 0.06680369989722508,
        "FLAT": 0.0,
        "UP": 0.9331963001027749,
    }
    assert updated["collapse_diagnostics_v2"]["predicted_distribution"] == {
        "DOWN": 0.06680369989722508,
        "FLAT": 0.0,
        "UP": 0.9331963001027749,
    }


def test_selected_policy_metrics_are_idempotent() -> None:
    candidate = {
        "decision_policy_grid_diagnostics": {
            "selected_policy": {
                "policy_id": "raw_argmax",
                "accuracy": 0.38,
                "baseline_accuracy": 0.40,
                "baseline_edge": -0.02,
                "predicted_ratios": {"DOWN": 0.10, "FLAT": 0.20, "UP": 0.70},
                "actual_ratios": {"DOWN": 0.30, "FLAT": 0.30, "UP": 0.40},
            }
        }
    }

    once = apply_selected_decision_policy_metrics(candidate)
    twice = apply_selected_decision_policy_metrics(once)

    assert once == twice
    assert twice["model_accuracy"] == 0.38
    assert twice["baseline_edge"] == -0.02
