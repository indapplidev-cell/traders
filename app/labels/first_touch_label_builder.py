from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.labels.direction_label_builder import DirectionLabelBuilder
from app.labels.label_config import (
    LABEL_MODE_FIRST_TOUCH_TP_SL,
    LABEL_MODE_FUTURE_CLOSE_ATR,
    LABEL_MODE_MFE_MAE_DOMINANCE,
    LABEL_MODE_SETUP_AWARE_FIRST_TOUCH,
    normalize_label_mode,
)
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP

FIRST_TOUCH_AMBIGUOUS = "AMBIGUOUS"
FIRST_TOUCH_NO_TRADE = "NO_TRADE"


def _config_value(config: Any, name: str, default: Any) -> Any:
    if isinstance(config, Mapping):
        value = config.get(name)
    else:
        value = getattr(config, name, None)
    return default if value is None else value


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def has_setup_context(features_json: Mapping[str, Any] | None) -> bool:
    return resolve_setup_type(features_json) != "no_setup"


def resolve_setup_type(features_json: Mapping[str, Any] | None) -> str:
    features = dict(features_json or {})
    nison_score = max(
        (_safe_float(value) for key, value in features.items() if str(key).startswith("nison_")),
        default=0.0,
    )
    alt_score = max(
        (_safe_float(value) for key, value in features.items() if str(key).startswith("alt_")),
        default=0.0,
    )
    path_score = max(
        (_safe_float(value) for key, value in features.items() if str(key).startswith("path_")),
        default=0.0,
    )
    support_distance = _safe_float(features.get("support_distance_atr"), 9.0)
    resistance_distance = _safe_float(features.get("resistance_distance_atr"), 9.0)
    near_support = bool(features.get("near_support")) or support_distance <= 0.35
    near_resistance = bool(features.get("near_resistance")) or resistance_distance <= 0.35

    if nison_score >= 0.55:
        return "nison_context"
    if alt_score >= 0.55:
        return "alt_context"
    if near_support or near_resistance:
        return "support_resistance_context"
    if path_score >= 0.55:
        return "path_context"
    return "no_setup"


class FirstTouchDirectionLabelBuilder:
    def build_label(
        self,
        current_candle: Any,
        future_candles: Sequence[Any],
        config: Any,
    ) -> dict[str, Any]:
        if not future_candles:
            return self._payload(
                direction=LABEL_FLAT,
                outcome=FIRST_TOUCH_NO_TRADE,
                bars_to_event=None,
                tp_hit=False,
                sl_hit=False,
                ambiguous=False,
                reason="future_window_empty",
            )

        current_close = _safe_float(getattr(current_candle, "close", None))
        atr_value = _safe_float(_config_value(config, "atr_value", None))
        take_profit_atr = _safe_float(_config_value(config, "take_profit_atr", 1.5), 1.5)
        stop_loss_atr = _safe_float(_config_value(config, "stop_loss_atr", 1.0), 1.0)

        if current_close == 0.0 or atr_value <= 0.0:
            return self._payload(
                direction=LABEL_FLAT,
                outcome=FIRST_TOUCH_NO_TRADE,
                bars_to_event=None,
                tp_hit=False,
                sl_hit=False,
                ambiguous=False,
                reason="missing_price_or_atr",
            )

        up_outcome = self._evaluate_side(
            future_candles=future_candles,
            take_profit_price=current_close + (take_profit_atr * atr_value),
            stop_price=current_close - (stop_loss_atr * atr_value),
            direction=LABEL_UP,
        )
        down_outcome = self._evaluate_side(
            future_candles=future_candles,
            take_profit_price=current_close - (take_profit_atr * atr_value),
            stop_price=current_close + (stop_loss_atr * atr_value),
            direction=LABEL_DOWN,
        )

        if up_outcome["outcome"] == "TP" and down_outcome["outcome"] == "TP":
            if up_outcome["bars_to_event"] == down_outcome["bars_to_event"]:
                return self._payload(
                    direction=FIRST_TOUCH_AMBIGUOUS,
                    outcome=FIRST_TOUCH_AMBIGUOUS,
                    bars_to_event=up_outcome["bars_to_event"],
                    tp_hit=True,
                    sl_hit=True,
                    ambiguous=True,
                    reason="same_bar_up_and_down_targets",
                )
            if int(up_outcome["bars_to_event"]) < int(down_outcome["bars_to_event"]):
                return self._payload(
                    direction=LABEL_UP,
                    outcome="TP",
                    bars_to_event=up_outcome["bars_to_event"],
                    tp_hit=True,
                    sl_hit=False,
                    ambiguous=False,
                    reason="upper_target_first",
                )
            return self._payload(
                direction=LABEL_DOWN,
                outcome="TP",
                bars_to_event=down_outcome["bars_to_event"],
                tp_hit=True,
                sl_hit=False,
                ambiguous=False,
                reason="lower_target_first",
            )

        if up_outcome["outcome"] == "TP":
            if down_outcome["outcome"] == FIRST_TOUCH_AMBIGUOUS and (
                down_outcome["bars_to_event"] is not None
                and int(down_outcome["bars_to_event"]) <= int(up_outcome["bars_to_event"])
            ):
                return self._payload(
                    direction=FIRST_TOUCH_AMBIGUOUS,
                    outcome=FIRST_TOUCH_AMBIGUOUS,
                    bars_to_event=down_outcome["bars_to_event"],
                    tp_hit=True,
                    sl_hit=True,
                    ambiguous=True,
                    reason="down_side_ambiguous_before_up_target",
                )
            return self._payload(
                direction=LABEL_UP,
                outcome="TP",
                bars_to_event=up_outcome["bars_to_event"],
                tp_hit=True,
                sl_hit=False,
                ambiguous=False,
                reason="upper_target_first",
            )

        if down_outcome["outcome"] == "TP":
            if up_outcome["outcome"] == FIRST_TOUCH_AMBIGUOUS and (
                up_outcome["bars_to_event"] is not None
                and int(up_outcome["bars_to_event"]) <= int(down_outcome["bars_to_event"])
            ):
                return self._payload(
                    direction=FIRST_TOUCH_AMBIGUOUS,
                    outcome=FIRST_TOUCH_AMBIGUOUS,
                    bars_to_event=up_outcome["bars_to_event"],
                    tp_hit=True,
                    sl_hit=True,
                    ambiguous=True,
                    reason="up_side_ambiguous_before_down_target",
                )
            return self._payload(
                direction=LABEL_DOWN,
                outcome="TP",
                bars_to_event=down_outcome["bars_to_event"],
                tp_hit=True,
                sl_hit=False,
                ambiguous=False,
                reason="lower_target_first",
            )

        ambiguous_bars = [
            item["bars_to_event"]
            for item in (up_outcome, down_outcome)
            if item["outcome"] == FIRST_TOUCH_AMBIGUOUS and item["bars_to_event"] is not None
        ]
        if ambiguous_bars:
            return self._payload(
                direction=FIRST_TOUCH_AMBIGUOUS,
                outcome=FIRST_TOUCH_AMBIGUOUS,
                bars_to_event=min(int(item) for item in ambiguous_bars),
                tp_hit=False,
                sl_hit=False,
                ambiguous=True,
                reason="same_side_same_bar_target_and_stop",
            )

        return self._payload(
            direction=LABEL_FLAT,
            outcome=FIRST_TOUCH_NO_TRADE,
            bars_to_event=None,
            tp_hit=False,
            sl_hit=False,
            ambiguous=False,
            reason="no_target_touch_within_horizon",
        )

    @staticmethod
    def _evaluate_side(
        *,
        future_candles: Sequence[Any],
        take_profit_price: float,
        stop_price: float,
        direction: str,
    ) -> dict[str, Any]:
        for index, candle in enumerate(future_candles, start=1):
            high_price = _safe_float(getattr(candle, "high", None))
            low_price = _safe_float(getattr(candle, "low", None))
            if direction == LABEL_UP:
                tp_hit = high_price >= take_profit_price
                sl_hit = low_price <= stop_price
            else:
                tp_hit = low_price <= take_profit_price
                sl_hit = high_price >= stop_price
            if tp_hit and sl_hit:
                return {"outcome": FIRST_TOUCH_AMBIGUOUS, "bars_to_event": index}
            if tp_hit:
                return {"outcome": "TP", "bars_to_event": index}
            if sl_hit:
                return {"outcome": "SL", "bars_to_event": index}
        return {"outcome": FIRST_TOUCH_NO_TRADE, "bars_to_event": None}

    @staticmethod
    def _payload(
        *,
        direction: str,
        outcome: str,
        bars_to_event: int | None,
        tp_hit: bool,
        sl_hit: bool,
        ambiguous: bool,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "first_touch_direction": direction,
            "first_touch_outcome": outcome,
            "first_touch_bars_to_event": bars_to_event,
            "first_touch_tp_hit": bool(tp_hit),
            "first_touch_sl_hit": bool(sl_hit),
            "first_touch_ambiguous": bool(ambiguous),
            "first_touch_reason": reason,
        }


def resolve_mfe_mae_dominance_label(
    *,
    up_move_atr: float,
    down_move_atr: float,
    direction_atr_threshold: float,
    flat_class_enabled: bool,
) -> str:
    if up_move_atr >= direction_atr_threshold and up_move_atr > down_move_atr:
        return LABEL_UP
    if down_move_atr >= direction_atr_threshold and down_move_atr > up_move_atr:
        return LABEL_DOWN
    return LABEL_FLAT if flat_class_enabled else LABEL_UP


def build_label_mode_snapshot(
    *,
    current_candle: Any,
    future_candles: Sequence[Any],
    atr_value: float,
    direction_atr_threshold: float,
    take_profit_atr: float,
    stop_loss_atr: float,
    flat_class_enabled: bool,
    features_json: Mapping[str, Any] | None = None,
    label_mode: str | None = None,
) -> dict[str, Any]:
    current_close = _safe_float(getattr(current_candle, "close", None))
    future_close = _safe_float(getattr(future_candles[-1], "close", None))
    future_return = 0.0 if current_close == 0.0 else (future_close / current_close) - 1
    future_move_atr = 0.0 if atr_value == 0.0 else (future_close - current_close) / atr_value
    up_move_atr = (
        max(_safe_float(getattr(future_candle, "high", None)) for future_candle in future_candles) - current_close
    ) / atr_value
    down_move_atr = (
        current_close - min(_safe_float(getattr(future_candle, "low", None)) for future_candle in future_candles)
    ) / atr_value
    future_close_label = DirectionLabelBuilder().build(
        future_return=future_return,
        atr=atr_value,
        current_close=current_close,
        direction_atr_threshold=direction_atr_threshold,
        flat_class_enabled=flat_class_enabled,
    )
    first_touch_payload = FirstTouchDirectionLabelBuilder().build_label(
        current_candle=current_candle,
        future_candles=future_candles,
        config={
            "atr_value": atr_value,
            "take_profit_atr": take_profit_atr,
            "stop_loss_atr": stop_loss_atr,
        },
    )
    first_touch_direction = str(first_touch_payload["first_touch_direction"])
    first_touch_label = (
        first_touch_direction if first_touch_direction in {LABEL_UP, LABEL_DOWN} else LABEL_FLAT
    )
    mfe_mae_dominance_label = resolve_mfe_mae_dominance_label(
        up_move_atr=up_move_atr,
        down_move_atr=down_move_atr,
        direction_atr_threshold=direction_atr_threshold,
        flat_class_enabled=flat_class_enabled,
    )
    setup_type = resolve_setup_type(features_json)
    setup_context_present = setup_type != "no_setup"
    setup_aware_first_touch_label = first_touch_label if setup_context_present else LABEL_FLAT

    mode_labels = {
        LABEL_MODE_FUTURE_CLOSE_ATR: future_close_label,
        LABEL_MODE_FIRST_TOUCH_TP_SL: first_touch_label,
        LABEL_MODE_MFE_MAE_DOMINANCE: mfe_mae_dominance_label,
        LABEL_MODE_SETUP_AWARE_FIRST_TOUCH: setup_aware_first_touch_label,
    }
    normalized_label_mode = normalize_label_mode(label_mode)
    return {
        "candle_open_time": getattr(current_candle, "open_time", None),
        "future_close_atr_label": future_close_label,
        "first_touch_tp_sl_label": first_touch_label,
        "mfe_mae_dominance_label": mfe_mae_dominance_label,
        "setup_aware_first_touch_label": setup_aware_first_touch_label,
        "selected_label_mode": normalized_label_mode,
        "selected_direction_label": mode_labels[normalized_label_mode],
        "future_return": float(future_return),
        "future_move_atr": float(future_move_atr),
        "up_move_atr": float(up_move_atr),
        "down_move_atr": float(down_move_atr),
        "max_favorable_move_atr": float(max(up_move_atr, down_move_atr)),
        "max_adverse_move_atr": float(min(up_move_atr, down_move_atr)),
        "has_setup_context": bool(setup_context_present),
        "setup_type": setup_type,
        "features_json": dict(features_json or {}),
        **first_touch_payload,
    }
