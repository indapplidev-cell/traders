"""Detect bounded, unprocessed profile-specific windows from closed DB candles."""

from __future__ import annotations

from app.engine_orchestrator.orchestrator_models import ClosedWindow
from app.engine_orchestrator.trade_profile import DEFAULT_TRADE_PROFILE_ID, resolve_trade_profile


class ClosedWindowDetector:
    def __init__(self, candle_repository: object, result_store: object, *, primary_timeframe: str = "5m",
                 trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID,
                 max_catchup_windows: int = 4, process_latest_only: bool = False) -> None:
        profile = resolve_trade_profile(trade_profile_id)
        if primary_timeframe != profile.trigger_timeframe:
            raise ValueError("closed-window detector timeframe/profile mismatch")
        if max_catchup_windows <= 0:
            raise ValueError("max_catchup_windows must be positive")
        self.candle_repository = candle_repository
        self.result_store = result_store
        self.primary_timeframe = primary_timeframe
        self.trade_profile_id = profile.trade_profile_id
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
        def processed(window: ClosedWindow) -> bool:
            return self.result_store.has_window(
                window.symbol, window.timeframe, window.closed_until_ms,
                trade_profile_id=self.trade_profile_id,
            )

        windows = [window for window in windows if not processed(window)]
        if self.process_latest_only and windows:
            return [windows[-1]]
        return windows[-self.max_catchup_windows:]

    def get_unprocessed_closed_windows_many(
        self, symbols: tuple[str, ...],
    ) -> dict[str, list[ClosedWindow]]:
        """Detect a complete universe with two bounded database queries."""
        loader = getattr(self.candle_repository, "get_recent_candles_for_symbols", None)
        existing_reader = getattr(self.result_store, "existing_window_keys", None)
        if not callable(loader) or not callable(existing_reader):
            return {symbol: self.get_unprocessed_closed_windows(symbol) for symbol in symbols}
        candles = loader(
            symbols, self.primary_timeframe, limit_per_symbol=self.max_catchup_windows,
        )
        candidates = {
            symbol: [
                ClosedWindow(symbol, self.primary_timeframe, int(candle.close_time_ms) + 1)
                for candle in candles.get(symbol, ())
                if bool(getattr(candle, "is_closed", False))
            ]
            for symbol in symbols
        }
        identities = [
            (window.symbol, window.timeframe, window.closed_until_ms)
            for windows in candidates.values() for window in windows
        ]
        existing = existing_reader(identities, trade_profile_id=self.trade_profile_id)
        result: dict[str, list[ClosedWindow]] = {}
        for symbol, windows in candidates.items():
            pending = [
                window for window in windows
                if (window.symbol, window.timeframe, window.closed_until_ms) not in existing
            ]
            if self.process_latest_only and pending:
                pending = [pending[-1]]
            result[symbol] = pending[-self.max_catchup_windows:]
        return result

    def latest_closed_boundary(self, symbol: str) -> int | None:
        candle = self.candle_repository.get_latest_closed_candle(symbol, self.primary_timeframe)
        return int(candle.close_time_ms) + 1 if candle is not None else None
