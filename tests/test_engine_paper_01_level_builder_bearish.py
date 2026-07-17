from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_bearish_geometry_uses_causal_resistance():
    context = {"reference_close": 100, "causal_resistance_level": 104,
               "causal_target_level": 90, "volatility_buffer": 1}
    plan = PaperRunner().process_risk_decision(
        risk_decision(direction_hint="BEARISH", risk_context=context))
    assert (plan.hypothetical_entry_reference, plan.hypothetical_stop_level,
            plan.hypothetical_target_level) == (100, 105, 90)
