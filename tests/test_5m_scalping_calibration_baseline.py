from app.engine_observation.scalping_calibration import aggregate, export_record, percentile
from scripts.observe_5m_scalping_calibration import boundary_count


def row(boundary=1_800_000_000_000, symbol="BTCUSDT", direction="BULLISH", reason=None):
    diagnostic = {
        "entry": 100, "atr": 1, "causal_invalidation": 99.5, "raw_stop": 99.25,
        "final_stop": 99.25, "stop_distance_bps": 75, "stop_envelope_bps": 80,
        "causal_target": 101.5, "target_source_type": "LOCAL_5M", "target_distance_bps": 150,
        "entry_fee_bps": 10, "exit_fee_bps": 10, "spread_bps": 1,
        "entry_slippage_bps": 2, "exit_slippage_bps": 2, "depth_impact_bps": 1,
        "safety_margin_bps": 3, "total_cost_bps": 29, "gross_rr": 2,
        "net_rr": 1.16, "expected_net_edge_bps": 121, "break_even_win_rate": .463,
        "target_available": True, "economic_gate_pass": True, "raw_reason": reason,
    }
    return {
        "boundary": boundary, "symbol": symbol, "profile": "trade-5m-v1",
        "parameter_set_id": "trade-5m-v1-runtime-v1-c141aece87c7f6a0", "duration_ms": 100,
        "analysis": {"regime": "UP"}, "setup": {"setup_status": "SETUP", "setup_type": "BREAKOUT"},
        "strategy": {"decision_status": "APPROVED", "direction_hint": direction},
        "risk": {"risk_status": "RISK_APPROVED", "direction_hint": direction},
        "paper": {"paper_status": "PAPER_PLAN_READY", "paper_direction": direction,
                  "paper_context": {"scalping_geometry_diagnostics": diagnostic},
                  "final_approval_generation": {"outcome": "CREATED"}},
        "module_reasons": {}, "risk_budget_reserved": False,
    }


def test_percentile_interpolates_and_empty_is_null():
    assert percentile([], .5) is None
    assert percentile([0, 10], .9) == 9


def test_export_preserves_null_and_normalizes_direction():
    value = export_record(row())
    assert value["direction"] == "LONG"
    assert value["net_pnl"] is None
    assert value["raw_reasons"] == []


def test_aggregate_funnel_cohorts_distribution_and_completeness():
    rows = [row(symbol=f"S{i}") for i in range(10)]
    value = aggregate(rows)
    assert value["sample_completeness"] == 1
    assert value["funnel"]["analysis"]["count"] == 10
    assert value["funnel"]["net_cost_viable"]["count"] == 10
    assert value["rr_cohorts"]["1.0"]["net_rr_pass"] == 10
    assert value["rr_cohorts"]["1.2"]["net_rr_pass"] == 0
    assert value["stop_distance"]["p90"] == 75


def test_repeat_opportunity_not_counted_as_independent_and_quota_free_rejection():
    first = row(reason="PAPER_REJECT_NEGATIVE_NET_EDGE")
    second = row(boundary=first["boundary"] + 300_000, reason="PAPER_REJECT_NEGATIVE_NET_EDGE")
    second["risk_budget_reserved"] = True
    value = aggregate([first, second], expected_symbols=1)
    assert value["raw_candidates"] == 2
    assert value["unique_causal_opportunities"] == 1
    assert value["repeat_observations"] == 1
    assert value["risk_budget_reservation_leaks"] == 1
    assert value["rejection_histogram"]["NEGATIVE_NET_EDGE"]["count"] == 2


def test_boundary_count_uses_fixed_read_only_bounded_query(monkeypatch):
    class Result:
        stdout = "144\n"

    seen = {}
    def run(command, **kwargs):
        seen["command"] = command
        return Result()

    monkeypatch.setattr("subprocess.run", run)
    assert boundary_count(1000, 288) == 144
    sql = seen["command"][-1]
    assert "SELECT count(*)" in sql and "LIMIT 288" in sql
    assert all(token not in sql.upper() for token in ("UPDATE ", "DELETE ", "INSERT ", "ALTER "))
