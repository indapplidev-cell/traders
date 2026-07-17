from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_unsupported_strategy_type_is_rejected():
    plan = PaperRunner().process_risk_decision(
        risk_decision(source_strategy_type="RANGE_REJECTION_RESEARCH"))
    assert plan.paper_status == "REJECT"
    assert "PAPER_REJECT_UNSUPPORTED_STRATEGY_TYPE" in plan.rejection_reasons
