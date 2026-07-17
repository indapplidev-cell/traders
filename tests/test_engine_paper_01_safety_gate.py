import pytest

from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


@pytest.mark.parametrize("flag", ["is_trade_signal", "is_executable", "order_approved",
                                   "execution_approved", "position_size_approved", "future_bars_used"])
def test_unsafe_source_is_rejected(flag):
    plan = PaperRunner().process_risk_decision(risk_decision(**{flag: True}))
    assert plan.paper_status == "REJECT"
    assert "PAPER_REJECT_UNSAFE_SOURCE_RISK_DECISION" in plan.rejection_reasons
    assert plan.future_bars_used is False
