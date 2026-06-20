from __future__ import annotations

from app.diagnostics.schwager_robustness_decision_board import (
    SchwagerRobustnessDecisionBoard,
)


def test_schwager_board_does_not_call_label_rework_when_two_stage_gate_passes() -> None:
    payload = SchwagerRobustnessDecisionBoard().evaluate(
        {
            "candidate_status": "REJECTED",
            "failed_gates": ["profit_aware_gate", "walk_forward_gate"],
            "baseline_edge": -0.01,
            "walk_forward_profit_factor": 0.97,
            "profit_factor": 0.95,
            "collapse_severity": "OK",
            "two_stage_trade_diagnostics": {
                "two_stage_quality_gate_passed": True,
                "anti_undertrading_gate_passed": True,
                "two_stage_quality_gate": {"passed": True},
                "anti_undertrading_gate": {"passed": True},
            },
            "book_driven_forensic_audit": {
                "label_ambiguity_audit": {"label_noise_rating": "HIGH_NOISE"},
                "feature_label_separability_audit": {"global_separability_rating": "GOOD"},
                "setup_context_audit": {
                    "groups_with_positive_edge": ["strong_0_75_1_00"],
                    "groups_with_negative_edge": [],
                },
                "schwager_negative_result_analyzer": {
                    "root_cause_bucket": "LABEL_AMBIGUITY_HIGH",
                    "primary_recommendation": "evaluate_first_touch_labels",
                },
            },
        }
    )

    assert payload["two_stage_quality_status"] == "PASSED"
    assert payload["primary_failure"] == "two_stage_needs_profit_validation"
    assert payload["final_research_decision"] == "TWO_STAGE_PROMISING_REJECTED_BY_PROFIT"
    assert "do_not_rework_labels_yet" in payload["what_not_to_do_next"]
