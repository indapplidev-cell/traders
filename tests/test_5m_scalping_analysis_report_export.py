from scripts.export_5m_scalping_analysis_report import _funnel, _stage_reason


def record(*, setup="REJECTED", setup_reason="NO_STRUCTURAL_SETUP"):
    return {
        "funnel_trace": {
            "analysis": {"status": "APPROVED"},
            "setup": {"status": setup, "reason_code": setup_reason},
            "strategy": {"status": "NOT_REACHED"},
            "geometry": {"status": "NOT_REACHED"},
            "cost": {"status": "NOT_REACHED"},
            "risk": {"status": "NOT_REACHED"},
            "paper_plan": {"status": "NOT_REACHED"},
            "final_approval": {"status": "NOT_REACHED"},
            "paper_command": {"status": "NOT_REACHED"},
            "position": {"status": "NOT_REACHED"},
            "exit": {"status": "NOT_REACHED"},
        },
        "first_rejection_stage": "STRUCTURAL_SETUP",
        "first_rejection_reason_code": "UNRELATED_ANALYSIS_DIAGNOSTIC",
    }


def test_funnel_is_sequential_and_validity_is_fail_closed():
    later = record(setup="APPROVED")
    later["first_rejection_stage"] = "STRATEGY_ELIGIBLE"
    later["funnel_trace"]["setup"] = {"status": "APPROVED"}
    funnel = _funnel([record(), later])
    values = {item["stage"]: item for item in funnel}
    assert values["ANALYSIS"]["pass"] == 2
    assert values["STRUCTURAL_SETUP"]["input"] == 2
    assert values["STRUCTURAL_SETUP"]["pass"] == 1
    assert values["STRATEGY_ADMITTED"]["input"] == 1
    assert values["VALIDITY_PASS"]["pass"] == 0


def test_stage_rejection_reason_uses_rejecting_trace_not_unrelated_raw_reason():
    assert _stage_reason(record()) == ("STRUCTURAL_SETUP", "NO_STRUCTURAL_SETUP")


def test_stage_reason_remaps_raw_economic_reason_to_cost_gate():
    value = record()
    value["first_rejection_stage"] = "PAPER_TRADE_PLAN"
    value["funnel_trace"]["paper_plan"] = {
        "status": "REJECTED", "reason_code": "PAPER_REJECT_NEGATIVE_NET_EDGE"
    }
    assert _stage_reason(value) == ("COST_GATE_PASS", "PAPER_REJECT_NEGATIVE_NET_EDGE")
