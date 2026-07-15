"""Validated configuration for multi-timeframe database synchronization."""

from dataclasses import dataclass, field

from app.config.settings import get_settings
from app.engine_market_data.timeframe_sync_plan import SYNC_PLAN


DEFAULT_WARMUP_LIMITS = {"1m": 3000, "5m": 2000, "15m": 1000, "1h": 1000, "4h": 1000, "1d": 1000}


@dataclass(slots=True)
class DBSyncConfig:
    symbols: list[str]
    enabled_timeframes: list[str] = field(default_factory=lambda: list(DEFAULT_WARMUP_LIMITS))
    primary_boundary_timeframe: str = "15m"
    warmup_limits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WARMUP_LIMITS))
    sync_plan: dict = field(default_factory=lambda: {key: {"on_boundary": value["on_boundary"], "required": dict(value["required"])} for key, value in SYNC_PLAN.items()})
    allow_rest_recovery: bool = True
    max_rest_limit: int = 1000
    store_only_closed_candles: bool = True
    database_url: str = field(default_factory=lambda: get_settings().database_url)

    def __post_init__(self) -> None:
        if not self.symbols: raise ValueError("at least one symbol is required")
        known = set(DEFAULT_WARMUP_LIMITS)
        if not set(self.enabled_timeframes) <= known: raise ValueError("unsupported enabled timeframe")
        if self.primary_boundary_timeframe not in SYNC_PLAN: raise ValueError("unsupported primary boundary")
        if not 1 <= self.max_rest_limit <= 1000: raise ValueError("max_rest_limit must be between 1 and 1000")
        if not self.store_only_closed_candles: raise ValueError("closed-candle-only policy cannot be disabled")


DBSyncSettings = DBSyncConfig
