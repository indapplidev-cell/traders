from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

EMA_DIRECTION_LONG = "LONG"
EMA_DIRECTION_SHORT = "SHORT"
EMA_DIRECTION_FLAT = "FLAT"

META_LABEL_WIN = "WIN"
META_LABEL_LOSS = "LOSS"
META_LABEL_AMBIGUOUS = "AMBIGUOUS"
META_LABEL_NO_EXIT = "NO_EXIT"
META_LABEL_NO_TRADE = "NO_TRADE"


@dataclass(slots=True)
class MetaLabelRecord:
    symbol: str
    interval: str
    candle_open_time: datetime
    feature_version: str
    label_version: str
    horizon_candles: int
    ema_signal_direction: str
    ema_signal_strength_atr: float | None
    meta_label: str
    meta_target_win: int | None
    meta_trade_r: float | None
    meta_same_candle_ambiguous: bool

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "candle_open_time": self.candle_open_time.isoformat(),
            "feature_version": self.feature_version,
            "label_version": self.label_version,
            "horizon_candles": self.horizon_candles,
            "ema_signal_direction": self.ema_signal_direction,
            "ema_signal_strength_atr": self.ema_signal_strength_atr,
            "meta_label": self.meta_label,
            "meta_target_win": self.meta_target_win,
            "meta_trade_r": self.meta_trade_r,
            "meta_same_candle_ambiguous": self.meta_same_candle_ambiguous,
        }


@dataclass(slots=True)
class MetaDatasetRow:
    symbol: str
    interval: str
    candle_open_time: datetime
    feature_version: str
    label_version: str
    horizon_candles: int
    features_json: dict[str, float | None]
    ema_signal_direction: str
    ema_signal_strength_atr: float
    meta_trade_r: float
    meta_target_win: int

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "candle_open_time": self.candle_open_time.isoformat(),
            "feature_version": self.feature_version,
            "label_version": self.label_version,
            "horizon_candles": self.horizon_candles,
            "ema_signal_direction": self.ema_signal_direction,
            "ema_signal_strength_atr": self.ema_signal_strength_atr,
            "meta_trade_r": self.meta_trade_r,
            "meta_target_win": self.meta_target_win,
        }
