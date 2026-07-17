from app.engine_risk.risk_runner import RiskRunner
from app.engine_risk.risk_store import RiskStore
from tests.engine_risk_01_helpers import strategy_decision


def test_store_is_idempotent_by_source_and_window():
    store = RiskStore()
    decision = RiskRunner(store=store).process_strategy_decision(strategy_decision())
    store.save(decision)
    assert store.count("btcusdt", "15m") == 1
    assert store.get_latest("BTCUSDT", "15m") == decision
    assert store.get_by_window("BTCUSDT", "15m", decision.closed_until_ms) == decision
