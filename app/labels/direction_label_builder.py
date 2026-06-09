from __future__ import annotations

from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


class DirectionLabelBuilder:
    def build(
        self,
        future_return: float,
        atr: float,
        current_close: float,
        direction_atr_threshold: float = 0.5,
        flat_class_enabled: bool = True,
    ) -> str:
        threshold = direction_atr_threshold * atr / current_close
        if future_return > threshold:
            return LABEL_UP
        if future_return < -threshold:
            return LABEL_DOWN
        if not flat_class_enabled:
            return LABEL_UP if future_return >= 0 else LABEL_DOWN
        return LABEL_FLAT
