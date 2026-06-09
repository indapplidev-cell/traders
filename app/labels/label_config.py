from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LabelConfig:
    label_version: str = "lv1"
    horizon_candles: int = 8
    direction_atr_threshold: float = 0.5
    take_profit_atr: float = 1.5
    stop_loss_atr: float = 1.0
    flat_class_enabled: bool = True
