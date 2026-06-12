from app.experiments.next_label_experiment_planner import NextLabelExperimentPlanner


def test_next_label_experiment_planner_recommends_for_collapse_profit_walk_and_gaps() -> None:
    planner = NextLabelExperimentPlanner()

    payload = planner.plan(
        {
            "experiment_id": "exp_plan",
            "best_candidate_config_id": "cfg_b",
            "best_candidate_status": "CANDIDATE_REJECTED",
            "top_failed_gate": "collapse_gate",
            "gate_failure_counts": {
                "collapse_gate": 2,
                "profit_aware_gate": 1,
                "walk_forward_gate": 2,
                "gap_quality_gate": 1,
                "baseline_edge_gate": 2,
            },
        }
    )

    recommendations = " ".join(payload["recommendations"])
    milestones = " ".join(payload["next_experiment_plan"]["milestones"])

    assert payload["planner_version"] == "ml30"
    assert "anti-collapse" in recommendations
    assert "TP/SL" in recommendations
    assert "walk-forward" in recommendations
    assert "gap handling" in recommendations
    assert "ML30" in milestones
    assert "ML31" in milestones
    assert payload["next_experiment_plan"]["focus_areas"]
