from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


def test_low_strategy_score_is_rejected():
    decision = RiskRunner().process_strategy_decision(strategy_decision(strategy_score=64.9))
    assert decision.risk_status == "REJECT"
    assert "RISK_REJECT_LOW_STRATEGY_SCORE" in decision.rejection_reasons
