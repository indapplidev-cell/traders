"""Database completeness verification for planned rolling windows."""

from dataclasses import dataclass

from app.engine_market_data.historical_backfill_planner import BackfillTask


@dataclass(frozen=True, slots=True)
class BackfillVerification:
    symbol: str
    timeframe: str
    expected_count: int
    actual_count: int
    missing_count: int
    missing_open_times: list[int]
    has_gaps: bool
    future_bars_used: bool
    closed_candle_only: bool
    status: str


class HistoricalBackfillVerifier:
    def __init__(self, repository: object) -> None:
        self.repository = repository

    def verify_task(self, task: BackfillTask) -> BackfillVerification:
        missing = self.repository.find_missing_open_times(task.symbol, task.timeframe,
                                                          task.expected_open_times)
        expected_set = set(task.expected_open_times)
        closed_only = True
        get_candles = getattr(self.repository, "get_candles", None)
        if get_candles is not None:
            rows = get_candles(task.symbol, task.timeframe, start_time_ms=task.start_open_time_ms,
                               end_time_ms=task.end_open_time_ms)
            closed_only = all(item.is_closed for item in rows if item.open_time_ms in expected_set)
        actual = task.limit - len(missing)
        has_gaps = bool(missing)
        status = "COMPLETE" if not has_gaps and closed_only else "INCOMPLETE"
        return BackfillVerification(task.symbol, task.timeframe, task.limit, actual, len(missing),
                                    list(missing), has_gaps, False, closed_only, status)

