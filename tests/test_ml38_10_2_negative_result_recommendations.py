from app.diagnostics.schwager_robustness_decision_board import (
    SchwagerRobustnessDecisionBoard,
)


def test_negative_result_recommendations_point_to_opportunity_first_rework() -> None:
    payload = SchwagerRobustnessDecisionBoard().evaluate(
        {
            "candidate_status": "REJECTED",
            "failed_gates": ["baseline_edge_gate", "collapse_gate"],
            "baseline_edge": -0.01,
            "walk_forward_profit_factor": 1.02,
            "profit_factor": 1.01,
            "collapse_severity": "OK",
            "book_driven_forensic_audit": {
                "setup_context_audit": {
                    "groups_with_positive_edge": ["support_retest"],
                    "groups_with_negative_edge": ["range_chop"],
                },
                "feature_label_separability_audit": {
                    "global_separability_rating": "GOOD",
                },
                "label_ambiguity_audit": {
                    "label_noise_rating": "GOOD",
                },
                "schwager_negative_result_analyzer": {
                    "root_cause_bucket": "SETUP_EDGE_ONLY",
                    "primary_recommendation": "build_opportunity_first_model",
                },
            },
            "opportunity_diagnostics": {
                "setup_edge_gate": {
                    "passed": False,
                    "opportunity_first_touch_success_rate": 0.61,
                },
                "opportunity_collapse_gate": {
                    "passed": True,
                },
                "opportunity_rate": 0.18,
            },
        }
    )

    assert payload["final_research_decision"] == "NEEDS_OPPORTUNITY_FIRST_REWORK"
    assert payload["primary_failure"] == "opportunity_first_needed"
    assert "do_not_soften_gates" in payload["what_not_to_do_next"]
    assert "do_not_run_full_grid" in payload["what_not_to_do_next"]
    assert "train_opportunity_first" in payload["what_to_do_next"]

