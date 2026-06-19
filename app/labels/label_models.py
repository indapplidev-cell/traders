from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

LABEL_UP = "UP"
LABEL_DOWN = "DOWN"
LABEL_FLAT = "FLAT"


@dataclass(slots=True)
class LabelRecord:
    symbol: str
    interval: str
    candle_open_time: datetime
    horizon_candles: int
    direction_label: str
    tp_before_sl: bool | None
    future_return: float
    future_move_atr: float
    max_favorable_move_atr: float
    max_adverse_move_atr: float
    label_version: str
    opportunity_label: int = 0
    opportunity_direction: str = "NONE"
    opportunity_reason: str = "no_setup"
    opportunity_score: float = 0.0
    setup_type: str = "no_setup"
    setup_quality_score: float = 0.0
    setup_invalidation_distance_atr: float = 0.0
    setup_expected_move_atr: float = 0.0
    label_ambiguity_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "candle_open_time": self.candle_open_time,
            "horizon_candles": self.horizon_candles,
            "direction_label": self.direction_label,
            "tp_before_sl": self.tp_before_sl,
            "future_return": self.future_return,
            "future_move_atr": self.future_move_atr,
            "max_favorable_move_atr": self.max_favorable_move_atr,
            "max_adverse_move_atr": self.max_adverse_move_atr,
            "label_version": self.label_version,
        }
