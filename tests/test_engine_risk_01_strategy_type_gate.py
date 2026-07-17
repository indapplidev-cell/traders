from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


def test_unsupported_strategy_type_is_rejected():
    decision = RiskRunner().process_strategy_decision(
        strategy_decision(strategy_type="PULLBACK_CONTINUATION_RESEARCH"))
    assert decision.risk_status == "REJECT"
    assert "RISK_REJECT_UNSUPPORTED_STRATEGY_TYPE" in decision.rejection_reasons
