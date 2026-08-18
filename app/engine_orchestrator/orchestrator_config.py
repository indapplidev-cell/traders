"""Validated runtime configuration for the online orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE
from app.engine_orchestrator.trade_profile import (
    DEFAULT_TRADE_PROFILE_ID,
    TradeSearchProfile,
    resolve_trade_profile,
)


DEFAULT_MINIMUM_WINDOWS = {"1m": 240, "5m": 288, "15m": 480, "1h": 240, "4h": 180, "1d": 240}


@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
    symbols: tuple[str, ...] = PREPARED_NEXT_TRADING_UNIVERSE.symbols
    trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID
    primary_timeframe: str = "15m"
    required_timeframes: tuple[str, ...] = ("1m", "5m", "15m", "1h", "4h", "1d")
    minimum_windows: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_MINIMUM_WINDOWS))
    poll_interval_seconds: float = 10.0
    health_report_interval_seconds: float = 60.0
    health_report_path: Path = Path("reports/engine_orchestrator/latest_health.json")
    max_catchup_windows: int = 4
    process_latest_only: bool = False
    require_all_timeframes_ok: bool = True
    allow_stale_higher_timeframes: bool = False
    trigger_source: str = "postgres_closed_candle"
    initial_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 60.0
    freshness_retry_interval_seconds: float = 5.0
    freshness_grace_seconds: float = 180.0
    freshness_max_attempts: int = 60
    waiting_batch_size: int = 100

    def __post_init__(self) -> None:
        profile = resolve_trade_profile(self.trade_profile_id)
        symbols = tuple(dict.fromkeys(normalize_market_symbol(value) for value in self.symbols))
        timeframes = tuple(dict.fromkeys(self.required_timeframes))
        if not symbols:
            raise ValueError("at least one symbol is required")
        if self.primary_timeframe != profile.trigger_timeframe:
            raise ValueError("primary_timeframe must match trade-profile trigger_timeframe")
        if self.primary_timeframe not in timeframes:
            raise ValueError("primary_timeframe must be required")
        for timeframe in timeframes:
            timeframe_to_milliseconds(timeframe)
            if int(self.minimum_windows.get(timeframe, 0)) <= 0:
                raise ValueError(f"positive minimum window required for {timeframe}")
        if self.poll_interval_seconds <= 0 or self.health_report_interval_seconds <= 0:
            raise ValueError("intervals must be positive")
        if self.max_catchup_windows <= 0:
            raise ValueError("max_catchup_windows must be positive")
        if self.initial_backoff_seconds <= 0 or self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("invalid backoff bounds")
        if self.freshness_retry_interval_seconds <= 0:
            raise ValueError("freshness_retry_interval_seconds must be positive")
        if self.freshness_grace_seconds <= 0:
            raise ValueError("freshness_grace_seconds must be positive")
        if self.freshness_max_attempts <= 0:
            raise ValueError("freshness_max_attempts must be positive")
        if self.waiting_batch_size <= 0:
            raise ValueError("waiting_batch_size must be positive")
        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "required_timeframes", timeframes)
        object.__setattr__(self, "health_report_path", Path(self.health_report_path))

    @property
    def trade_profile(self) -> TradeSearchProfile:
        return resolve_trade_profile(self.trade_profile_id)
