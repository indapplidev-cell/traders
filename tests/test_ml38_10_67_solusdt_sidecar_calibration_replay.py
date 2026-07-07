from app.diagnostics.solusdt_sidecar_calibration_replay import (
    denominator_mismatch,
    solusdt_sidecar_calibration_replay as replay,
)


def test_identity_and_previous_stage_contract() -> None:
    assert replay["diagnostic_name"] == "solusdt_sidecar_calibration_replay"
    assert replay["diagnostic_version"] == "ml38.10.67"
    assert replay["execution_mode"] == "READ_ONLY_CALIBRATION_REPLAY_NO_TRAINING_NO_RERUN"
    previous = replay["previous_stage_summary"]
    assert previous["previous_stage"] == "ML38.10.66"
    assert previous["previous_decision"] == "POST_FIX_SOLUSDT_QUALITY_TRIAGE_COMPLETED_NEXT_ACTION_SELECTED"


def test_all_real_sidecar_sets_validate_without_mutation() -> None:
    validation = replay["sidecar_set_validation"]
    assert validation["sidecar_sets_found"] == 45
    assert validation["complete_sets"] == 45
    assert validation["incomplete_sets"] == 0
    assert validation["latest_sha256"] == "5ef2a0492f33686e5885fe9d2128bf223df8d4b7c0f0939fd3486f0d8100f3c4"
    assert validation["latest_sha256_observed"] is True
    assert validation["all_exact_byte_valid"] is True
    assert validation["all_lf_only_valid"] is True
    assert validation["all_schema_valid"] is True
    assert validation["all_summary_contract_valid"] is True
    assert validation["real_artifacts_mutated"] is False


def test_probability_discovery_and_policy_replay_are_explicit() -> None:
    discovery = replay["probability_field_discovery"]
    assert discovery["raw_probability_fields_found"] is False
    assert discovery["raw_probability_status"] == "RAW_PROBABILITIES_NOT_AVAILABLE_IN_SIDECAR"
    assert discovery["calibrated_probability_fields_found"] is True
    assert isinstance(discovery["replay_possible"], bool)
    assert discovery["replay_possible"] is True
    assert replay["policy_grid_results"]
    summary = replay["candidate_calibration_replay_summary"]
    assert summary["candidates_replayed"] == 45
    assert summary["policies_tested"] == 19
    assert summary["candidate_policy_pairs_tested"] == 855


def test_current_baseline_keeps_selected_policy_and_sidecar_layers_separate() -> None:
    baseline = replay["current_distribution_baseline"]
    assert baseline["actual_distribution"]["FLAT"] == 899
    assert baseline["current_predicted_distribution"]["FLAT"] == 109
    assert baseline["sidecar_stored_argmax_distribution"] == {"DOWN": 532, "FLAT": 15, "UP": 426}
    assert baseline["current_accuracy_edge"] < 0.0


def test_h08_denominator_contract_is_diagnosed_without_fix() -> None:
    contract = replay["h08_denominator_contract"]
    assert contract["produced_rows"] == 6485
    assert contract["expected_rows"] == 6481
    assert contract["delta_rows"] == 4
    assert contract["contract_test_added"] is True
    assert contract["fix_applied"] is False
    synthetic = denominator_mismatch(6485, 6481)
    assert synthetic == {"produced_rows": 6485, "expected_rows": 6481, "delta_rows": 4, "mismatch": True}


def test_guardrails_and_decision_remain_fail_closed() -> None:
    guardrails = replay["guardrails"]
    assert guardrails["quick_quality_rerun_during_stage"] is False
    assert guardrails["wrapper_execute_used_during_stage"] is False
    assert guardrails["training_or_runtime_executed_during_stage"] is False
    assert guardrails["existing_real_artifacts_mutated"] is False
    assert guardrails["new_real_sidecars_created"] is False
    assert guardrails["new_zip_created"] is False
    gate = replay["decision_gate"]
    assert gate["cascade_outcome_allowed_now"] is False
    assert gate["production_like_recompute_allowed_now"] is False
    assert gate["tradable_edge_claim_allowed_now"] is False
    assert replay["next_action_recommendation"]
    assert replay["next_action_recommendation"]["recommended_stage"] == "ML38.10.68"

