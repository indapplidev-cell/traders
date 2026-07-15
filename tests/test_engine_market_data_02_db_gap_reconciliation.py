from app.engine_market_data.db_gap_reconciliation import DBGapReconciliation
from app.engine_market_data.db_sync_config import DBSyncConfig
from engine_market_data_02_helpers import MemoryRepository, Rest, candle


def test_gap_reconciliation_never_synthesizes_unavailable_candle():
    reconciliation = DBGapReconciliation(MemoryRepository([candle("1m", 0)]), Rest([]), DBSyncConfig(["BTCUSDT"]))
    assert reconciliation.find_db_gaps("BTCUSDT", "1m", 0, 120_000) == [60_000, 120_000]
    report = reconciliation.reconcile_db_gaps("BTCUSDT", "1m", 0, 120_000)
    assert report.missing_after == 2 and report.status in {"DEGRADED", "PARTIAL"}
