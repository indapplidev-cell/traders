from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class DatasetRow:
    symbol: str
    interval: str
    candle_open_time: datetime
    feature_version: str
    label_version: str
    horizon_candles: int
    features_json: dict[str, float | None]
    direction_label: str
    tp_before_sl: bool | None
    future_return: float
    future_move_atr: float
    max_favorable_move_atr: float
    max_adverse_move_atr: float

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "candle_open_time": self.candle_open_time.isoformat(),
            "feature_version": self.feature_version,
            "label_version": self.label_version,
            "horizon_candles": self.horizon_candles,
            "direction_label": self.direction_label,
            "tp_before_sl": self.tp_before_sl,
            "future_return": self.future_return,
            "future_move_atr": self.future_move_atr,
            "max_favorable_move_atr": self.max_favorable_move_atr,
            "max_adverse_move_atr": self.max_adverse_move_atr,
        }
