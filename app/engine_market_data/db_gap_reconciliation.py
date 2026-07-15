"""Expected-open-time gap audit; never synthesizes market data."""

from app.engine_market_data.db_sync_config import DBSyncConfig
from app.engine_market_data.db_sync_report import SyncReport
from app.engine_market_data.multi_timeframe_sync import MultiTimeframeSync
from app.engine_market_data.timeframe import timeframe_to_milliseconds


def expected_open_times_in_range(timeframe: str, start_time_ms: int, end_time_ms: int) -> list[int]:
    duration = timeframe_to_milliseconds(timeframe)
    if start_time_ms < 0 or end_time_ms < start_time_ms: return []
    first = start_time_ms + (-start_time_ms % duration)
    return list(range(first, end_time_ms + 1, duration))


class DBGapReconciliation:
    def __init__(self, repository: object, rest_client: object, config: DBSyncConfig) -> None:
        self.repository = repository
        self.sync = MultiTimeframeSync(repository, rest_client, config.sync_plan, config)

    def find_db_gaps(self, symbol: str, timeframe: str, start_time_ms: int,
                     end_time_ms: int) -> list[int]:
        expected = expected_open_times_in_range(timeframe, start_time_ms, end_time_ms)
        return self.repository.find_missing_open_times(symbol, timeframe, expected)

    def reconcile_db_gaps(self, symbol: str, timeframe: str, start_time_ms: int,
                          end_time_ms: int) -> SyncReport:
        expected = expected_open_times_in_range(timeframe, start_time_ms, end_time_ms)
        return self.sync.reconcile_timeframe(symbol, timeframe, expected)


DatabaseGapReconciliation = DBGapReconciliation
