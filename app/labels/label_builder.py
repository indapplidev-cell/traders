from __future__ import annotations

from collections import Counter
from typing import Any

from app.features.technical_indicators import TechnicalIndicators
from app.labels.direction_label_builder import DirectionLabelBuilder
from app.labels.label_config import LabelConfig
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP, LabelRecord
from app.labels.tp_sl_label_builder import TpSlLabelBuilder


class LabelBuilder:
    def __init__(
        self,
        direction_label_builder: DirectionLabelBuilder | None = None,
        tp_sl_label_builder: TpSlLabelBuilder | None = None,
    ) -> None:
        self._direction_label_builder = direction_label_builder or DirectionLabelBuilder()
        self._tp_sl_label_builder = tp_sl_label_builder or TpSlLabelBuilder()

    def build(
        self,
        candles: list[Any],
        symbol: str,
        interval: str,
        horizon_candles: int,
        label_version: str,
        direction_atr_threshold: float = 0.5,
        take_profit_atr: float = 1.5,
        stop_loss_atr: float = 1.0,
        flat_class_enabled: bool = True,
        config: LabelConfig | None = None,
    ) -> list[LabelRecord]:
        if not candles:
            return []

        if config is not None:
            horizon_candles = config.horizon_candles
            label_version = config.label_version
            direction_atr_threshold = config.direction_atr_threshold
            take_profit_atr = config.take_profit_atr
            stop_loss_atr = config.stop_loss_atr
            flat_class_enabled = config.flat_class_enabled

        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]
        closes = [float(candle.close) for candle in candles]
        atr_14 = TechnicalIndicators.atr(highs, lows, closes, 14)

        records: list[LabelRecord] = []
        for index, candle in enumerate(candles):
            if index + horizon_candles >= len(candles):
                break

            atr_value = atr_14[index]
            current_close = closes[index]
            if atr_value is None or atr_value == 0 or current_close == 0:
                continue

            future_window = candles[index + 1 : index + 1 + horizon_candles]
            future_close = float(future_window[-1].close)
            future_return = (future_close / current_close) - 1
            future_move_atr = (future_close - current_close) / atr_value

            up_move_atr = (max(float(future_candle.high) for future_candle in future_window) - current_close) / atr_value
            down_move_atr = (current_close - min(float(future_candle.low) for future_candle in future_window)) / atr_value

            direction_label = self._direction_label_builder.build(
                future_return=future_return,
                atr=atr_value,
                current_close=current_close,
                direction_atr_threshold=direction_atr_threshold,
                flat_class_enabled=flat_class_enabled,
            )
            tp_before_sl = self._tp_sl_label_builder.build(
                direction_label=direction_label,
                current_close=current_close,
                atr=atr_value,
                future_candles=future_window,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
            )

            if direction_label == LABEL_DOWN:
                max_favorable_move_atr = down_move_atr
                max_adverse_move_atr = up_move_atr
            elif direction_label == LABEL_UP:
                max_favorable_move_atr = up_move_atr
                max_adverse_move_atr = down_move_atr
            else:
                max_favorable_move_atr = max(up_move_atr, down_move_atr)
                max_adverse_move_atr = min(up_move_atr, down_move_atr)

            records.append(
                LabelRecord(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=candle.open_time,
                    horizon_candles=horizon_candles,
                    direction_label=direction_label,
                    tp_before_sl=tp_before_sl,
                    future_return=float(future_return),
                    future_move_atr=float(future_move_atr),
                    max_favorable_move_atr=float(max_favorable_move_atr),
                    max_adverse_move_atr=float(max_adverse_move_atr),
                    label_version=label_version,
                )
            )

        return records

    def summarize(self, records: list[LabelRecord]) -> dict[str, int]:
        counts = Counter(record.direction_label for record in records)
        return {
            LABEL_UP: counts.get(LABEL_UP, 0),
            LABEL_DOWN: counts.get(LABEL_DOWN, 0),
            LABEL_FLAT: counts.get(LABEL_FLAT, 0),
        }
