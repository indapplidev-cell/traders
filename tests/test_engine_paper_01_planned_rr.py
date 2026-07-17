from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_planned_rr_calculation_and_minimum_gate():
    assert PaperRunner().process_risk_decision(risk_decision()).planned_rr == 1.66666667
    context = {"reference_close": 100, "causal_support_level": 95,
               "causal_target_level": 105, "volatility_buffer": 1}
    low = PaperRunner().process_risk_decision(risk_decision(risk_context=context))
    assert low.paper_status == "REJECT"
    assert "PAPER_REJECT_LOW_PLANNED_RR" in low.rejection_reasons
