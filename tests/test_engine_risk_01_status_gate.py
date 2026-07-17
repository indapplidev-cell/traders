import pytest

from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


@pytest.mark.parametrize(("source", "expected"), [
    ("NO_DECISION", "NO_DECISION"), ("WAIT", "WAIT"),
    ("REJECT", "REJECT"), ("ERROR", "ERROR"),
])
def test_source_status_routing(source, expected):
    assert RiskRunner().process_strategy_decision(
        strategy_decision(decision_status=source)).risk_status == expected
