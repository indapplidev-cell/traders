"""Independent public, closed-candle-only market-data layer."""

from app.engine_market_data.binance_kline_ws import BinanceKlineWebSocketClient, ReconnectPolicy
from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_market_data.candle import Candle
from app.engine_market_data.candle_store import CandleStore
from app.engine_market_data.candle_stream import CandleStream, ClosedCandleEvent
from app.engine_market_data.exchange_time_sync import ExchangeTimeSync, TimeSyncResult
from app.engine_market_data.gap_detector import Gap, GapDetector, detect_gap, find_missing_open_times
from app.engine_market_data.gap_recovery import GapRecovery, GapRecoveryReport
from app.engine_market_data.market_data_health import MarketDataHealth, MarketDataHealthStatus
from app.engine_market_data.market_data_snapshot import (
    MarketDataSnapshot, build_market_data_snapshot, build_market_data_snapshot_from_db,
)
from app.engine_market_data.boundary_scheduler import BoundaryEvent, BoundaryScheduler
from app.engine_market_data.db_sync_config import DBSyncConfig
from app.engine_market_data.db_sync_report import SyncReport, SyncStatus
from app.engine_market_data.multi_timeframe_sync import MultiTimeframeSync
from app.engine_market_data.historical_backfill_config import HistoricalBackfillConfig
from app.engine_market_data.historical_backfill_planner import (
    BackfillRange, BackfillTask, HistoricalBackfillPlan, HistoricalBackfillPlanner,
    group_missing_open_times_into_ranges, split_backfill_range,
)
from app.engine_market_data.historical_backfill_report import (
    BackfillStatus, BackfillTaskReport, HistoricalBackfillReport,
)
from app.engine_market_data.historical_backfill_runner import HistoricalBackfillRunner
from app.engine_market_data.historical_backfill_verifier import (
    BackfillVerification, HistoricalBackfillVerifier,
)
from app.engine_market_data.timeframe import (
    expected_next_open_time,
    floor_timestamp_to_timeframe,
    is_aligned_to_timeframe,
    timeframe_to_milliseconds,
)

__all__ = [
    "BinanceKlineWebSocketClient", "BinancePublicRestClient", "Candle", "CandleStore",
    "CandleStream", "ClosedCandleEvent", "ExchangeTimeSync", "Gap", "GapDetector",
    "GapRecovery", "GapRecoveryReport", "MarketDataHealth", "MarketDataHealthStatus",
    "BoundaryEvent", "BoundaryScheduler", "DBSyncConfig", "MarketDataSnapshot",
    "MultiTimeframeSync", "ReconnectPolicy", "SyncReport", "SyncStatus", "TimeSyncResult",
    "BackfillRange", "BackfillStatus", "BackfillTask", "BackfillTaskReport",
    "BackfillVerification", "HistoricalBackfillConfig", "HistoricalBackfillPlan",
    "HistoricalBackfillPlanner", "HistoricalBackfillReport", "HistoricalBackfillRunner",
    "HistoricalBackfillVerifier", "group_missing_open_times_into_ranges", "split_backfill_range",
    "build_market_data_snapshot", "build_market_data_snapshot_from_db",
    "detect_gap", "expected_next_open_time", "find_missing_open_times",
    "floor_timestamp_to_timeframe", "is_aligned_to_timeframe", "timeframe_to_milliseconds",
]
