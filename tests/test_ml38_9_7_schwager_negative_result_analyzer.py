from app.diagnostics.schwager_negative_result_analyzer import SchwagerNegativeResultAnalyzer


def test_schwager_negative_result_analyzer_flags_weak_raw_class_separation() -> None:
    payload = SchwagerNegativeResultAnalyzer().evaluate(
        {
            "candidate_status": "REJECTED",
            "failed_gates": ["collapse_gate", "walk_forward_gate"],
            "baseline_edge": -0.02,
            "model_accuracy": 0.33,
            "baseline_accuracy": 0.41,
            "collapse_severity": "CRITICAL",
            "walk_forward_profit_factor": 0.97,
            "profit_factor": 0.95,
            "prediction_root_cause_audit": {
                "warnings": ["actual_down_rows_mapped_to_up"],
            },
            "feature_label_separability_audit": {
                "global_separability_rating": "WEAK",
            },
            "label_ambiguity_audit": {
                "label_noise_rating": "WATCH",
            },
            "setup_context_audit": {
                "groups_with_positive_edge": [],
            },
        }
    )

    assert payload["diagnostic_name"] == "schwager_negative_result_analyzer"
    assert payload["root_cause_bucket"] in {
        "WEAK_RAW_CLASS_SEPARATION",
        "GLOBAL_DIRECTION_TASK_TOO_NOISY",
    }
    assert payload["primary_recommendation"] == "do_not_tune_class_weights_yet"

