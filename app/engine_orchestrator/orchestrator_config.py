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
from app.engine_orchestrator.runtime_parameters import (
    RuntimeProfileParameters,
    resolve_runtime_parameters,
)
from app.config.trade_parameters import SCALPING_V2
from app.config.yaml_authority import RUNTIME_POLICY


DEFAULT_MINIMUM_WINDOWS = dict(SCALPING_V2.signal.market_data_windows)
_ORCHESTRATOR = RUNTIME_POLICY.orchestrator


@dataclass(frozen=True, slots=True)
class OrchestratorConfig:
    symbols: tuple[str, ...] = _ORCHESTRATOR.symbols
    trade_profile_id: str = DEFAULT_TRADE_PROFILE_ID
    primary_timeframe: str = SCALPING_V2.signal.timeframe
    required_timeframes: tuple[str, ...] = SCALPING_V2.signal.required_timeframes
    minimum_windows: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_MINIMUM_WINDOWS))
    poll_interval_seconds: float = _ORCHESTRATOR.poll_interval_seconds
    health_report_interval_seconds: float = _ORCHESTRATOR.health_report_interval_seconds
    health_report_path: Path = Path(_ORCHESTRATOR.health_report_path)
    max_catchup_windows: int = _ORCHESTRATOR.max_catchup_windows
    process_latest_only: bool = _ORCHESTRATOR.process_latest_only
    require_all_timeframes_ok: bool = _ORCHESTRATOR.require_all_timeframes_ok
    allow_stale_higher_timeframes: bool = _ORCHESTRATOR.allow_stale_higher_timeframes
    trigger_source: str = _ORCHESTRATOR.trigger_source
    initial_backoff_seconds: float = _ORCHESTRATOR.initial_backoff_seconds
    max_backoff_seconds: float = _ORCHESTRATOR.max_backoff_seconds
    freshness_retry_interval_seconds: float = _ORCHESTRATOR.freshness_retry_interval_seconds
    freshness_grace_seconds: float = _ORCHESTRATOR.freshness_grace_seconds
    freshness_max_attempts: int = _ORCHESTRATOR.freshness_max_attempts
    waiting_batch_size: int = _ORCHESTRATOR.waiting_batch_size

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
            if timeframe not in self.minimum_windows or int(self.minimum_windows[timeframe]) <= 0:
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

    @property
    def runtime_parameters(self) -> RuntimeProfileParameters:
        return resolve_runtime_parameters(self.trade_profile_id)
