from app.engine_risk.risk_config import RiskConfig
from app.engine_risk.risk_policy import RiskPolicy
from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


def test_research_limit_rejects_excess():
    config = RiskConfig(max_research_preapprovals_per_symbol_per_day=1,
                        max_research_preapprovals_total_per_day=2,
                        max_research_preapprovals_per_direction_per_day=2)
    runner = RiskRunner(RiskPolicy(config))
    first = runner.process_strategy_decision(strategy_decision(decision_id="strategy:1"))
    second = runner.process_strategy_decision(strategy_decision(decision_id="strategy:2", closed_until_ms=1_700_000_001_000))
    assert first.risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert second.risk_status == "REJECT"
    assert "RISK_REJECT_RESEARCH_LIMIT_EXCEEDED" in second.rejection_reasons
