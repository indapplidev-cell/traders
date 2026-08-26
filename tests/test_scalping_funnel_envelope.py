from app.engine_observation.scalping_funnel_envelope import diagnose_scalping_funnel


def test_target_funnel_is_diagnostic_and_never_a_quota():
    result = diagnose_scalping_funnel({
        "evaluations": 2880, "setups": 500, "strategy_candidates": 200,
        "geometry_valid": 100, "net_cost_viable": 50,
        "final_approvals": 30, "actual_entries": 20,
    })
    assert result["diagnostic_only"] is True
    assert result["admission_quota"] is False
    assert all(row["status"] == "WITHIN_ENVELOPE" for row in result["stages"].values())


def test_missing_and_outside_counts_are_described_not_rejected():
    result = diagnose_scalping_funnel({"evaluations": 1, "setups": 999})
    assert result["stages"]["evaluations"]["status"] == "BELOW_ENVELOPE"
    assert result["stages"]["setups"]["status"] == "ABOVE_ENVELOPE"
    assert result["stages"]["actual_entries"]["status"] == "NOT_OBSERVED"
