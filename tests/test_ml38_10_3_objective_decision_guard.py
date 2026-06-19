from __future__ import annotations

from app.diagnostics.class_margin_objective_decision import (
    evaluate_class_margin_objective_decision,
    load_latest_class_margin_runtime_evidence,
)


def test_class_margin_decision_blocks_when_runtime_reports_are_missing(tmp_path) -> None:
    payload = load_latest_class_margin_runtime_evidence(tmp_path / "missing_reports")

    assert payload["diagnostic_name"] == "class_margin_objective_decision"
    assert payload["class_margin_objective_allowed"] is False
    assert payload["reason"] == "required_runtime_evidence_missing"
    assert "schwager_robustness_decision_board.final_research_decision" in payload["missing_diagnostics"]


def test_class_margin_decision_blocks_on_label_rework_board() -> None:
    payload = evaluate_class_margin_objective_decision(
        {
            "schwager_robustness_decision_board": {
                "final_research_decision": "NEEDS_LABEL_REWORK",
            },
            "feature_label_separability_audit": {
                "global_separability_rating": "GOOD",
            },
            "label_ambiguity_audit": {
                "label_noise_rating": "GOOD",
            },
        }
    )

    assert payload["class_margin_objective_allowed"] is False
    assert payload["reason"] == "blocked_by_decision_board:needs_label_rework"


def test_class_margin_decision_allows_ready_board() -> None:
    payload = evaluate_class_margin_objective_decision(
        {
            "schwager_robustness_decision_board": {
                "final_research_decision": "READY_FOR_MODEL_OBJECTIVE_REWORK",
            },
            "feature_label_separability_audit": {
                "global_separability_rating": "GOOD",
            },
            "label_ambiguity_audit": {
                "label_noise_rating": "WATCH",
            },
        }
    )

    assert payload["class_margin_objective_allowed"] is True
    assert payload["reason"] == "decision_board_ready_for_model_objective_rework"
