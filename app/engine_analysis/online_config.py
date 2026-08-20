"""Configuration for running engine_analysis on live closed-candle windows."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine_analysis.analysis_contract import RECOMMENDED_CONTEXT_CANDLES


@dataclass(slots=True)
class OnlineAnalysisConfig:
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    required_history_candles: int = RECOMMENDED_CONTEXT_CANDLES
    max_snapshot_age_ms: int = 300_000
    run_on_closed_candle_only: bool = True
    allow_degraded_market_data: bool = False
    dedupe_by_closed_until: bool = True
    store_snapshots: bool = True
    runtime_parameter_set_id: str = "legacy-analysis-defaults"
    atr_lookback_candles: int = 14
    impulse_lookback_candles: int = 96
    structure_lookback_candles: int = 96
    analysis_decision_candles: int = 24
    confirmation_window_candles: int = 3
    volume_baseline_candles: int = 93
    breakout_volume_baseline_candles: int = 20
    regime_lookback_candles: int = 96

    def __post_init__(self) -> None:
        if self.required_history_candles < 1:
            raise ValueError("required_history_candles must be positive")
        if self.max_snapshot_age_ms < 0:
            raise ValueError("max_snapshot_age_ms must be non-negative")
        if min(
            self.atr_lookback_candles,
            self.impulse_lookback_candles,
            self.structure_lookback_candles,
            self.analysis_decision_candles,
            self.confirmation_window_candles,
            self.volume_baseline_candles,
            self.breakout_volume_baseline_candles,
            self.regime_lookback_candles,
        ) < 1:
            raise ValueError("analysis profile lookbacks must be positive")
        if (
            self.runtime_parameter_set_id != "legacy-analysis-defaults"
            and self.required_history_candles < self.regime_lookback_candles
        ):
            raise ValueError("required history must cover regime lookback")
        if (
            self.runtime_parameter_set_id != "legacy-analysis-defaults"
            and self.regime_lookback_candles < self.structure_lookback_candles
        ):
            raise ValueError("regime lookback must cover structure lookback")
        if not self.runtime_parameter_set_id.strip():
            raise ValueError("runtime_parameter_set_id must not be empty")
        self.symbols = [str(symbol).strip().upper() for symbol in self.symbols]
        self.timeframes = [str(timeframe).strip() for timeframe in self.timeframes]
        if any(not value for value in (*self.symbols, *self.timeframes)):
            raise ValueError("symbols and timeframes must not contain empty values")
