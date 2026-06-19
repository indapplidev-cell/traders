from app.diagnostics.schwager_robustness_decision_board import (
    SchwagerRobustnessDecisionBoard,
)


def test_schwager_robustness_decision_board_marks_label_rework() -> None:
    payload = SchwagerRobustnessDecisionBoard().evaluate(
        {
            "candidate_selection": {
                "candidate_status": "REJECTED",
                "failed_gates": ["collapse_gate", "walk_forward_gate"],
            },
            "baseline_edge": -0.03,
            "walk_forward_profit_factor": 0.97,
            "profit_factor": 0.95,
            "collapse_severity": "WATCH",
            "book_driven_forensic_audit": {
                "label_ambiguity_audit": {
                    "label_noise_rating": "HIGH_NOISE",
                },
                "feature_label_separability_audit": {
                    "global_separability_rating": "GOOD",
                },
                "setup_context_audit": {
                    "groups_with_positive_edge": [],
                    "groups_with_negative_edge": ["range_chop"],
                },
                "schwager_negative_result_analyzer": {
                    "root_cause_bucket": "LABEL_AMBIGUITY_HIGH",
                    "primary_recommendation": "evaluate_first_touch_labels",
                },
            },
        }
    )

    assert payload["diagnostic_name"] == "schwager_robustness_decision_board"
    assert payload["final_research_decision"] == "NEEDS_LABEL_REWORK"
    assert payload["primary_failure"] == "label_noise_high"
    assert "inspect_first_touch_labels" in payload["what_to_do_next"]

