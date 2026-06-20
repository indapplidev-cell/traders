from __future__ import annotations

from collections import Counter
from typing import Any

from app.features.technical_indicators import TechnicalIndicators
from app.labels.label_config import LabelConfig, normalize_label_mode
from app.labels.first_touch_label_builder import build_label_mode_snapshot
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP, LabelRecord
from app.labels.opportunity_label_builder import OpportunityLabelBuilder
from app.labels.tp_sl_label_builder import TpSlLabelBuilder


class LabelBuilder:
    def __init__(
        self,
        direction_label_builder: DirectionLabelBuilder | None = None,
        tp_sl_label_builder: TpSlLabelBuilder | None = None,
    ) -> None:
        self._direction_label_builder = direction_label_builder
        self._tp_sl_label_builder = tp_sl_label_builder or TpSlLabelBuilder()
        self._opportunity_label_builder = OpportunityLabelBuilder()
        self._last_label_mode_rows: list[dict[str, Any]] = []

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
        feature_rows: list[Any] | None = None,
    ) -> list[LabelRecord]:
        if not candles:
            return []

        label_mode = normalize_label_mode(None if config is None else config.label_mode)
        if config is not None:
            horizon_candles = config.horizon_candles
            label_version = config.label_version
            direction_atr_threshold = config.direction_atr_threshold
            take_profit_atr = config.take_profit_atr
            stop_loss_atr = config.stop_loss_atr
            flat_class_enabled = config.flat_class_enabled
            label_mode = normalize_label_mode(config.label_mode)

        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]
        closes = [float(candle.close) for candle in candles]
        atr_14 = TechnicalIndicators.atr(highs, lows, closes, 14)
        feature_map: dict[Any, dict[str, Any]] = {}
        for row in feature_rows or []:
            if isinstance(row, dict):
                candle_open_time = row.get("candle_open_time")
                features_json = dict(row.get("features_json", {}))
            else:
                candle_open_time = getattr(row, "candle_open_time", None)
                features_json = dict(getattr(row, "features_json", {}))
            feature_map[candle_open_time] = features_json

        records: list[LabelRecord] = []
        mode_rows: list[dict[str, Any]] = []
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

            snapshot = build_label_mode_snapshot(
                current_candle=candle,
                future_candles=future_window,
                atr_value=atr_value,
                direction_atr_threshold=direction_atr_threshold,
                take_profit_atr=take_profit_atr,
                stop_loss_atr=stop_loss_atr,
                flat_class_enabled=flat_class_enabled,
                features_json=feature_map.get(candle.open_time),
                label_mode=label_mode,
            )
            direction_label = str(snapshot["selected_direction_label"])
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
            opportunity_payload = self._opportunity_label_builder.build(
                features_json=feature_map.get(candle.open_time),
                direction_label=direction_label,
                tp_before_sl=tp_before_sl,
                future_move_atr=float(future_move_atr),
                max_favorable_move_atr=float(max_favorable_move_atr),
                max_adverse_move_atr=float(max_adverse_move_atr),
                config=config,
            )

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
                    opportunity_label=opportunity_payload.opportunity_label,
                    opportunity_direction=opportunity_payload.opportunity_direction,
                    opportunity_reason=opportunity_payload.opportunity_reason,
                    opportunity_score=opportunity_payload.opportunity_score,
                    setup_type=opportunity_payload.setup_type,
                    setup_quality_score=opportunity_payload.setup_quality_score,
                    setup_invalidation_distance_atr=opportunity_payload.setup_invalidation_distance_atr,
                    setup_expected_move_atr=opportunity_payload.setup_expected_move_atr,
                    label_ambiguity_score=opportunity_payload.label_ambiguity_score,
                )
            )
            mode_rows.append({**snapshot, **opportunity_payload.to_dict()})

        self._last_label_mode_rows = mode_rows
        return records

    def summarize(self, records: list[LabelRecord]) -> dict[str, int]:
        counts = Counter(record.direction_label for record in records)
        return {
            LABEL_UP: counts.get(LABEL_UP, 0),
            LABEL_DOWN: counts.get(LABEL_DOWN, 0),
            LABEL_FLAT: counts.get(LABEL_FLAT, 0),
        }

    def last_label_mode_rows(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._last_label_mode_rows]
