from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


def test_not_marked_for_review_is_no_decision():
    source = strategy_decision()
    object.__setattr__(source, "requires_risk_review", False)
    assert RiskRunner().process_strategy_decision(source).risk_status == "NO_DECISION"
