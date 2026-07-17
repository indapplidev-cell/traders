import pytest

from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


@pytest.mark.parametrize("quality", ["WEAK", "REJECTED", "WAITING", "UNKNOWN", "ERROR"])
def test_low_quality_is_not_preapproved(quality):
    decision = RiskRunner().process_strategy_decision(strategy_decision(strategy_quality=quality))
    assert decision.risk_status == "REJECT"


@pytest.mark.parametrize("quality", ["GOOD", "ACCEPTABLE"])
def test_good_and_acceptable_are_eligible(quality):
    decision = RiskRunner().process_strategy_decision(strategy_decision(strategy_quality=quality))
    assert decision.risk_status == "RISK_PRE_APPROVED_RESEARCH"
