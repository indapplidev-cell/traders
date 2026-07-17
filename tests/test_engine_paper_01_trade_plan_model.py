from dataclasses import fields

from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_ready_plan_is_permanently_paper_only():
    plan = PaperRunner().process_risk_decision(risk_decision())
    assert plan.paper_status == "PAPER_PLAN_READY"
    assert plan.paper_only is True
    for name in ("is_executable", "is_trade_signal", "order_approved", "execution_approved",
                 "position_opened", "position_size_approved", "future_bars_used"):
        assert getattr(plan, name) is False
    assert {item.name for item in fields(type(plan))} >= {"planned_rr", "paper_context"}
