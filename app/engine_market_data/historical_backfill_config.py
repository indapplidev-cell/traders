"""Validated configuration for rolling historical candle backfill."""

from dataclasses import dataclass, field

from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


DEFAULT_BACKFILL_LIMITS: dict[str, int] = {
    "1m": 10_000,
    "5m": 10_000,
    "15m": 10_000,
    "1h": 5_000,
    "4h": 3_000,
    "1d": 1_500,
}


@dataclass(slots=True)
class HistoricalBackfillConfig:
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT"])
    timeframes: list[str] = field(default_factory=lambda: list(DEFAULT_BACKFILL_LIMITS))
    backfill_limits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_BACKFILL_LIMITS))
    batch_limit: int = 1000
    max_rest_limit: int = 1000
    rest_retry_attempts: int = 3
    rest_backoff_seconds: float = 0.25
    verify_after_backfill: bool = True
    fail_on_unrecovered_gaps: bool = False
    utc_only: bool = True
    store_only_closed_candles: bool = True

    def __post_init__(self) -> None:
        if not self.symbols:
            raise ValueError("at least one symbol is required")
        self.symbols = list(dict.fromkeys(normalize_market_symbol(value) for value in self.symbols))
        if not self.timeframes:
            raise ValueError("at least one timeframe is required")
        self.timeframes = list(dict.fromkeys(self.timeframes))
        for timeframe in self.timeframes:
            timeframe_to_milliseconds(timeframe)
            if timeframe not in self.backfill_limits or self.backfill_limits[timeframe] <= 0:
                raise ValueError(f"a positive backfill limit is required for {timeframe}")
        if not 1 <= self.batch_limit <= 1000:
            raise ValueError("batch_limit must be between 1 and 1000")
        if not 1 <= self.max_rest_limit <= 1000:
            raise ValueError("max_rest_limit must be between 1 and 1000")
        if self.rest_retry_attempts < 0:
            raise ValueError("rest_retry_attempts must be non-negative")
        if self.rest_backoff_seconds < 0:
            raise ValueError("rest_backoff_seconds must be non-negative")
        if not self.utc_only:
            raise ValueError("historical backfill requires UTC-only time")
        if not self.store_only_closed_candles:
            raise ValueError("closed-candle-only policy cannot be disabled")

