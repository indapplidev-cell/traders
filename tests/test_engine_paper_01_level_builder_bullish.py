from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_bullish_geometry_uses_causal_support():
    plan = PaperRunner().process_risk_decision(risk_decision())
    assert plan.hypothetical_entry_reference == 100
    assert plan.hypothetical_invalidation_level == 95
    assert plan.hypothetical_stop_level == 94
    assert plan.hypothetical_target_level == 110
