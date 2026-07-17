import pytest

from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


@pytest.mark.parametrize("flag", ["is_trade_signal", "is_executable", "risk_approved", "future_bars_used"])
def test_unsafe_source_is_rejected(flag):
    source = strategy_decision()
    object.__setattr__(source, flag, True)
    decision = RiskRunner().process_strategy_decision(source)
    assert decision.risk_status == "REJECT"
    assert "RISK_REJECT_UNSAFE_SOURCE_DECISION" in decision.rejection_reasons or flag == "future_bars_used"
