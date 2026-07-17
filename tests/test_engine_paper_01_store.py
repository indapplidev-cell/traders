from app.engine_paper.paper_runner import PaperRunner
from app.engine_paper.paper_store import PaperStore
from tests.engine_paper_01_helpers import risk_decision


def test_store_is_idempotent_by_window_and_source():
    store = PaperStore()
    plan = PaperRunner(store=store).process_risk_decision(risk_decision())
    store.save(plan)
    assert store.count("btcusdt", "15m") == 1
    assert store.get_latest("BTCUSDT", "15m") == plan
    assert store.get_by_window("BTCUSDT", "15m", plan.closed_until_ms) == plan
