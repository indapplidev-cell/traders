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
    opportunity_label: int = 0
    opportunity_direction: str = "NONE"
    opportunity_reason: str = "no_setup"
    opportunity_score: float = 0.0
    setup_type: str = "no_setup"
    setup_quality_score: float = 0.0
    setup_invalidation_distance_atr: float = 0.0
    setup_expected_move_atr: float = 0.0
    label_ambiguity_score: float = 1.0

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
            "opportunity_label": self.opportunity_label,
            "opportunity_direction": self.opportunity_direction,
            "opportunity_reason": self.opportunity_reason,
            "opportunity_score": self.opportunity_score,
            "setup_type": self.setup_type,
            "setup_quality_score": self.setup_quality_score,
            "setup_invalidation_distance_atr": self.setup_invalidation_distance_atr,
            "setup_expected_move_atr": self.setup_expected_move_atr,
            "label_ambiguity_score": self.label_ambiguity_score,
        }
