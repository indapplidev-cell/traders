from app.engine_observation.scalping_journal import build_scalping_evaluation_journal


def test_evaluation_journal_preserves_inputs_and_unknown_outcomes_as_null():
    row = build_scalping_evaluation_journal(
        profile="trade-5m-v1", parameter_set_id="params", boundary_ms=123,
        symbol="BTCUSDT", analysis={"analysis_context": {"regime": "UP"}},
        setup={"setup_id": "s", "direction_hint": "BULLISH"},
        strategy={"strategy_score": 65, "context": {"raw_score": 72}},
        risk={"risk_status": "RISK_PRE_APPROVED_RESEARCH"},
        paper={"shadow_plan": {"paper_context": {
            "scalping_geometry_diagnostics": {
                "entry": 100, "final_stop": 99, "causal_target": 102,
                "total_cost_bps": 30, "net_rr": 1.5,
            }
        }}},
    )
    assert row["profile"] == "trade-5m-v1"
    assert row["strategy"]["raw_score"] == 72
    assert row["geometry"]["entry"] == 100
    assert row["economics"]["total_cost_bps"] == 30
    assert row["execution"] is None
    assert row["mfe_bps"] is None and row["net_pnl"] is None
