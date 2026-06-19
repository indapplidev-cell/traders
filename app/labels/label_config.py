from __future__ import annotations

from dataclasses import dataclass

LABEL_MODE_FUTURE_CLOSE_ATR = "future_close_atr"
LABEL_MODE_FIRST_TOUCH_TP_SL = "first_touch_tp_sl"
LABEL_MODE_MFE_MAE_DOMINANCE = "mfe_mae_dominance"
LABEL_MODE_SETUP_AWARE_FIRST_TOUCH = "setup_aware_first_touch"

SUPPORTED_LABEL_MODES = (
    LABEL_MODE_FUTURE_CLOSE_ATR,
    LABEL_MODE_FIRST_TOUCH_TP_SL,
    LABEL_MODE_MFE_MAE_DOMINANCE,
    LABEL_MODE_SETUP_AWARE_FIRST_TOUCH,
)


def normalize_label_mode(label_mode: str | None) -> str:
    if label_mode in SUPPORTED_LABEL_MODES:
        return str(label_mode)
    return LABEL_MODE_FUTURE_CLOSE_ATR


@dataclass(slots=True)
class LabelConfig:
    label_version: str = "lv1"
    horizon_candles: int = 8
    direction_atr_threshold: float = 0.5
    take_profit_atr: float = 1.5
    stop_loss_atr: float = 1.0
    flat_class_enabled: bool = True
    label_mode: str = LABEL_MODE_FUTURE_CLOSE_ATR
