from scripts.forensic_postfix_setup_regime import economics, observation_row, task_a


def test_postfix_target_validation_does_not_reproduce_old_miss():
    row = {"cycle_boundary": 200, "selected_target": 101.0, "all_causal_targets": [
        {"price": 101.0, "source": "LOCAL_5M", "timeframe": "5m", "future_safe": True, "directionally_valid": True},
        {"price": 103.0, "source": "STRUCTURAL", "timeframe": "5m", "future_safe": True, "directionally_valid": True, "net_rr": 1.0}],
        "farther_causal_targets": [{"price": 103.0, "source": "STRUCTURAL", "timeframe": "5m", "future_safe": True,
                                    "directionally_valid": True, "net_rr": 1.0}],
        "selector_missed_dynamic_valid_target": False, "final_required_rr": .8, "selector_selected_index": 1,
        "candidate_id": "c", "opportunity_id": "o", "symbol": "BTCUSDT", "side": "LONG", "rr_pass": True,
        "net_rr": 1.0, "dynamic_required_rr": .8}
    _, report = task_a([row], 100, {"cycle_boundary": 200})
    assert report["final_verdict"] == "POSTFIX_TARGET_FIX_VALIDATED"
    assert report["farther_target_missed_count"] == 0


def test_actual_impulse_and_regime_fields_drive_forensic():
    raw = {"observation_id": "obs", "identity": {"boundary_time_ms": 1, "opportunity_id": "opp", "symbol": "XRPUSDT"},
           "analysis": {"impulse_state": "NO_IMPULSE", "confidence": .25, "raw": {"impulse_phase": "NO_IMPULSE",
               "reason_codes": ["COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN", "COMPOSER_UNKNOWN_REGIME_SELECTED"],
               "analysis_context": {"quality_basis": {"impulse_context": {"impulse_move_pct": .5, "atr_pct": .2}},
                                    "scalping": {"base_regime": "UNKNOWN", "market_regime": "EXPANSION",
                                                 "entry_evidence_evaluation": {"status": "NOT_EVALUATED"}}}}},
           "setup": {"direction": "BEARISH", "type": "SCALP_MOMENTUM_CONTINUATION", "raw": {"status": "SETUP_CANDIDATE", "regime": "UNKNOWN"}},
           "current_production_decision_trace": {}}
    row = observation_row(raw, None)
    assert row["impulse"] == "NO_IMPULSE"
    assert row["regime"] == "UNKNOWN"
    assert row["impulse_reject_subreason"] == "MOVE_BELOW_ABSOLUTE_3PCT_FLOOR"
    assert row["momentum_state"] == "EXPANSION"


def test_frequency_uses_exact_exposure_hours():
    metrics = economics([{"entry": 1, "selected_stop": 0.9, "selected_target": 1.1, "rr_input": True,
                          "rr_pass": False, "net_outcome_r": -1, "net_rr": .5, "final_required_rr": 1.0}], 2.0)
    assert metrics["candidates_per_hour"] == .5
    assert metrics["rr_inputs_per_hour"] == .5
