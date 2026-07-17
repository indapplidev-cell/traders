from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_wrong_side_stop_or_target_is_rejected():
    context = {"reference_close": 100, "causal_support_level": 101,
               "causal_target_level": 110, "volatility_buffer": 0.5}
    plan = PaperRunner().process_risk_decision(risk_decision(risk_context=context))
    assert plan.paper_status == "REJECT"
    assert "PAPER_REJECT_INVALID_LEVEL_GEOMETRY" in plan.rejection_reasons
