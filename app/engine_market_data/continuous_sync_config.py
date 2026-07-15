"""Validated operational configuration for ENGINE-MARKET-DATA-04."""

from dataclasses import dataclass, field

from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


SUPPORTED_SYNC_TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_WARMUP_DEPTHS = {"1m": 1440, "5m": 2016, "15m": 2016, "1h": 720, "4h": 720, "1d": 365}
DEFAULT_GAP_CHECK_WINDOWS = {"1m": 360, "5m": 288, "15m": 192, "1h": 168, "4h": 180, "1d": 365}
FRESHNESS_ALLOWANCE_MS = {"1m": 10_000, "5m": 15_000, "15m": 20_000, "1h": 60_000, "4h": 90_000, "1d": 120_000}
GAP_CHECK_INTERVAL_MS = {"1m": 300_000, "5m": 300_000, "15m": 300_000,
                         "1h": 3_600_000, "4h": 3_600_000, "1d": 86_400_000}


@dataclass(slots=True)
class ContinuousSyncConfig:
    symbols: list[str] = field(default_factory=lambda: list(DEFAULT_SYMBOLS))
    timeframes: list[str] = field(default_factory=lambda: list(SUPPORTED_SYNC_TIMEFRAMES))
    warmup: bool = True
    continuous: bool = True
    gap_check: bool = True
    dry_run: bool = False
    warmup_depths: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WARMUP_DEPTHS))
    gap_check_windows: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_GAP_CHECK_WINDOWS))
    freshness_allowance_ms: dict[str, int] = field(default_factory=lambda: dict(FRESHNESS_ALLOWANCE_MS))
    poll_interval_seconds: float = 1.0
    health_report_interval_seconds: float = 60.0
    max_rest_batch_size: int = 1000
    backoff_initial_seconds: float = 2.0
    backoff_max_seconds: float = 60.0
    stop_after_cycles: int | None = None
    health_report_path: str | None = None
    daemon_instance_id: str | None = None

    def __post_init__(self) -> None:
        self.symbols = [normalize_market_symbol(value) for value in self.symbols]
        self.timeframes = list(dict.fromkeys(self.timeframes))
        if not self.symbols:
            raise ValueError("at least one symbol is required")
        if not self.timeframes or not set(self.timeframes) <= set(SUPPORTED_SYNC_TIMEFRAMES):
            raise ValueError("unsupported or empty timeframe selection")
        for timeframe in self.timeframes:
            timeframe_to_milliseconds(timeframe)
            for mapping, name in ((self.warmup_depths, "warmup depth"),
                                  (self.gap_check_windows, "gap check window"),
                                  (self.freshness_allowance_ms, "freshness allowance")):
                if not isinstance(mapping.get(timeframe), int) or mapping[timeframe] <= 0:
                    raise ValueError(f"{name} for {timeframe} must be positive")
        if not 1 <= self.max_rest_batch_size <= 1000:
            raise ValueError("max_rest_batch_size must be between 1 and 1000")
        if self.poll_interval_seconds <= 0 or self.health_report_interval_seconds <= 0:
            raise ValueError("poll and health report intervals must be positive")
        if self.backoff_initial_seconds <= 0 or self.backoff_max_seconds < self.backoff_initial_seconds:
            raise ValueError("invalid backoff limits")
        if self.stop_after_cycles is not None and self.stop_after_cycles <= 0:
            raise ValueError("stop_after_cycles must be positive")

