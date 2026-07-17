from dataclasses import fields

import pytest

from app.engine_risk.risk_decision import RiskDecision
from app.engine_risk.risk_errors import RiskContractError
from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


def test_decision_hard_codes_non_execution_flags():
    decision = RiskRunner().process_strategy_decision(strategy_decision())
    for name in ("execution_approved", "order_approved", "position_size_approved",
                 "is_executable", "is_trade_signal", "future_bars_used"):
        assert getattr(decision, name) is False
        assert next(item for item in fields(RiskDecision) if item.name == name).init is False
    assert decision.risk_pre_approved and decision.requires_execution_review


def test_preapproval_flags_cannot_be_used_on_reject():
    source = RiskRunner().process_strategy_decision(strategy_decision())
    payload = source.to_dict()
    for key in ("execution_approved", "order_approved", "position_size_approved",
                "is_executable", "is_trade_signal", "future_bars_used"):
        payload.pop(key)
    payload.update(risk_status="REJECT", risk_level="BLOCKED")
    with pytest.raises(RiskContractError):
        RiskDecision(**payload)
