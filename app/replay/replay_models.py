from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ReplayResultRecord:
    session_id: str
    model_version: str
    symbol: str
    interval: str
    candle_open_time: datetime
    predicted_direction: str
    actual_direction: str
    prob_up: float
    prob_down: float
    prob_flat: float
    was_correct: bool
    error_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "model_version": self.model_version,
            "symbol": self.symbol,
            "interval": self.interval,
            "candle_open_time": self.candle_open_time,
            "predicted_direction": self.predicted_direction,
            "actual_direction": self.actual_direction,
            "prob_up": self.prob_up,
            "prob_down": self.prob_down,
            "prob_flat": self.prob_flat,
            "was_correct": self.was_correct,
            "error_score": self.error_score,
        }
