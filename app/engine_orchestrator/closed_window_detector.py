"""Detect bounded, unprocessed 15-minute windows from closed DB candles."""

from __future__ import annotations

from app.engine_orchestrator.orchestrator_models import ClosedWindow


class ClosedWindowDetector:
    def __init__(self, candle_repository: object, result_store: object, *, primary_timeframe: str = "15m",
                 max_catchup_windows: int = 4, process_latest_only: bool = False) -> None:
        if primary_timeframe != "15m":
            raise ValueError("closed-window detector supports the 15m online trigger only")
        if max_catchup_windows <= 0:
            raise ValueError("max_catchup_windows must be positive")
        self.candle_repository = candle_repository
        self.result_store = result_store
        self.primary_timeframe = primary_timeframe
        self.max_catchup_windows = max_catchup_windows
        self.process_latest_only = process_latest_only

    def get_unprocessed_closed_windows(self, symbol: str) -> list[ClosedWindow]:
        candles = self.candle_repository.get_candles(
            symbol, self.primary_timeframe, limit=self.max_catchup_windows
        )
        windows = [
            ClosedWindow(symbol, self.primary_timeframe, int(candle.close_time_ms) + 1)
            for candle in candles if bool(getattr(candle, "is_closed", False))
        ]
        windows = [window for window in windows if not self.result_store.has_window(
            window.symbol, window.timeframe, window.closed_until_ms
        )]
        if self.process_latest_only and windows:
            return [windows[-1]]
        return windows[-self.max_catchup_windows:]

    def latest_closed_boundary(self, symbol: str) -> int | None:
        candle = self.candle_repository.get_latest_closed_candle(symbol, self.primary_timeframe)
        return int(candle.close_time_ms) + 1 if candle is not None else None
