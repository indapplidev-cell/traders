import pytest

from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


@pytest.mark.parametrize("direction", ["NEUTRAL", "NONE"])
def test_non_directional_source_is_rejected(direction):
    decision = RiskRunner().process_strategy_decision(strategy_decision(direction_hint=direction))
    assert decision.risk_status == "REJECT"
