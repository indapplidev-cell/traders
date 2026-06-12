from app.evaluation.model_quality_validator import (
    INSUFFICIENT_REAL_HISTORY,
    validate_model_quality,
)


def test_ml36_1_model_quality_validator_is_none_safe() -> None:
    result = validate_model_quality(
        training_summary=None,
        baseline_summary=None,
        probability_diagnostics=None,
        calibration_summary=None,
        profit_aware_summary={"gate_results": None},
        walk_forward_summary=None,
        gate_policy_replay_summary=None,
        candidate_selection_summary={
            "warnings": None,
            "recommendations": None,
            "failed_gates": None,
            "passed_gates": None,
        },
        regime_label_builder_status_summary=None,
    )

    payload = result.to_dict()

    assert payload["quality_status"] == INSUFFICIENT_REAL_HISTORY
    assert "probability_diagnostics_not_provided" in payload["warnings"]
    assert payload["candidate_selection"]["warnings"] == []
    assert payload["candidate_selection"]["failed_gates"] == []
    assert payload["regime_label_builder_status"]["regime_label_builder_status"] == "blocked"
    assert payload["regime_label_builder_status"]["reason"] == "regime_label_builder_status_not_provided"

