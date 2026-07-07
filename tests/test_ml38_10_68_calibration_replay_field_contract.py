from copy import deepcopy

from app.diagnostics.calibration_replay_field_contract import (
    CALIBRATED_FIELDS,
    RAW_FIELDS,
    calibration_replay_field_contract as diagnostic,
    classify_replay_payload,
    compute_outcome_metrics,
)


def _complete_rows():
    return [
        {"row_alignment_key": "a", "actual_label": "FLAT", "current_predicted_label": "FLAT",
         "raw_prob_down": .2, "raw_prob_flat": .6, "raw_prob_up": .2,
         "calibrated_prob_down": .1, "calibrated_prob_flat": .8, "calibrated_prob_up": .1,
         "fold_id": "f0", "profit_join_key": "p0"},
        {"row_alignment_key": "b", "actual_label": "UP", "current_predicted_label": "UP",
         "raw_prob_down": .1, "raw_prob_flat": .2, "raw_prob_up": .7,
         "calibrated_prob_down": .1, "calibrated_prob_flat": .1, "calibrated_prob_up": .8,
         "fold_id": "f0", "profit_join_key": "p1"},
    ]


def test_identity_previous_stage_and_current_sidecar_contract():
    assert diagnostic["diagnostic_name"] == "calibration_replay_field_contract"
    assert diagnostic["diagnostic_version"] == "ml38.10.68"
    assert diagnostic["execution_mode"] == "DIAGNOSTIC_FIELD_CONTRACT_NO_TRAINING_NO_RERUN"
    previous = diagnostic["previous_stage_summary"]
    assert previous["previous_stage"] == "ML38.10.67"
    assert previous["previous_decision"] == "CALIBRATION_REPLAY_INCOMPLETE_MISSING_PROBABILITY_FIELDS"
    current = diagnostic["current_sidecar_field_status"]
    assert current["sidecar_sets_checked"] == 45
    assert current["current_compact_sidecar_has_calibrated_probabilities"] is True
    assert current["current_compact_sidecar_has_raw_probabilities"] is False
    assert current["current_compact_sidecar_has_row_level_actual_label"] is False
    assert current["current_compact_sidecar_supports_distribution_replay"] is True
    assert current["current_compact_sidecar_supports_outcome_ranking"] is False


def test_required_contract_contains_probability_identity_and_alignment_fields():
    names = {item["field_name"] for item in diagnostic["required_row_alignment_contract"]["fields"]}
    assert {"actual_label", "split", "row_alignment_key", "sidecar_argmax_label", "current_predicted_label"} <= names
    assert set(RAW_FIELDS) <= names
    assert set(CALIBRATED_FIELDS) <= names


def test_prediction_layers_are_explicit_and_not_conflated():
    mapping = diagnostic["prediction_layer_mapping"]
    assert mapping["downstream_policy_output_distribution"] == {"DOWN": 472, "FLAT": 109, "UP": 392}
    assert mapping["sidecar_stored_calibrated_softmax_argmax_distribution"] == {"DOWN": 532, "FLAT": 15, "UP": 426}
    assert mapping["best_distribution_only_policy_distribution"] == {"DOWN": 281, "FLAT": 400, "UP": 292}
    assert "must not be conflated" in mapping["source_layer_warning"]
    assert mapping["best_distribution_only_policy_should_be_implemented_next"] is False


def test_complete_row_aligned_payload_allows_outcome_replay():
    capability = classify_replay_payload(_complete_rows())
    assert capability["outcome_aware_replay_supported"] is True
    assert capability["raw_vs_calibrated_replay_supported"] is True
    assert capability["fold_profit_ranking_supported"] is True
    metrics = compute_outcome_metrics(_complete_rows())
    assert set(("accuracy", "majority_baseline_accuracy", "accuracy_edge", "flat_recall", "false_directional_on_actual_flat")) <= metrics.keys()


def test_missing_fields_fail_closed_by_capability():
    rows = _complete_rows()
    missing_raw = deepcopy(rows)
    for row in missing_raw:
        row.pop("raw_prob_down")
    assert classify_replay_payload(missing_raw)["raw_vs_calibrated_replay_supported"] is False
    missing_actual = deepcopy(rows)
    for row in missing_actual:
        row.pop("actual_label")
    assert classify_replay_payload(missing_actual)["outcome_aware_replay_supported"] is False
    missing_alignment = deepcopy(rows)
    for row in missing_alignment:
        row.pop("row_alignment_key")
    assert classify_replay_payload(missing_alignment)["safe_external_join_supported"] is False
    missing_fold_profit = deepcopy(rows)
    for row in missing_fold_profit:
        row.pop("fold_id"); row.pop("profit_join_key")
    capability = classify_replay_payload(missing_fold_profit)
    assert capability["outcome_aware_replay_supported"] is True
    assert capability["fold_profit_ranking_supported"] is False


def test_compact_payload_is_incomplete():
    compact = [{"calibrated_prob_down": .4, "calibrated_prob_flat": .2, "calibrated_prob_up": .4,
                "row_alignment_key": "SOLUSDT:15m:t0"}]
    capability = classify_replay_payload(compact)
    assert capability["distribution_replay_supported"] is True
    assert capability["status"] == "INCOMPLETE_FOR_OUTCOME_AWARE_REPLAY"
    assert diagnostic["synthetic_replay_contract"]["compact_sidecar_classified_incomplete"] is True


def test_h08_is_documented_but_not_fixed():
    h08 = diagnostic["h08_scope_boundary"]
    assert h08["h08_candidate_boundary_total"] == 6485
    assert h08["h08_expected_global_denominator"] == 6481
    assert h08["h08_delta_rows"] == 4
    assert h08["h08_fix_applied_in_ml38_10_68"] is False


def test_guardrails_decision_and_next_action_fail_closed():
    guardrails = diagnostic["guardrails"]
    assert guardrails["training_or_runtime_executed_during_stage"] is False
    assert guardrails["wrapper_execute_used_during_stage"] is False
    assert guardrails["existing_real_artifacts_mutated"] is False
    assert guardrails["labels_builders_gates_model_logic_changed"] is False
    assert guardrails["class_weights_changed"] is False
    assert guardrails["production_calibration_logic_changed"] is False
    assert guardrails["directional_confidence_floor_implemented"] is False
    assert guardrails["flat_override_implemented"] is False
    gate = diagnostic["decision_gate"]
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False
    assert diagnostic["implementation_recommendation"]["action_type"] == "SIDECAR_FIELD_CONTRACT_IMPLEMENTATION"

