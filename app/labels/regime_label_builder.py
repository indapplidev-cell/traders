from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from app.features.technical_indicators import TechnicalIndicators
from app.labels.direction_label_builder import DirectionLabelBuilder
from app.labels.label_config import LabelConfig
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP, LabelRecord
from app.labels.regime_label_config import RegimeLabelConfigPlanner
from app.labels.tp_sl_label_builder import TpSlLabelBuilder


@dataclass(slots=True)
class RegimeLabelBuilderResult:
    records: list[LabelRecord]
    regime_label_builder_status: str
    regime_label_builder_available: bool
    regime_label_builder_used_in_training: bool
    regime_specific_labeling_available: bool
    regime_specific_training_applied: bool
    regime_label_config_used: dict[str, str]
    label_distribution_by_regime: dict[str, dict[str, int]]
    missing_requirements: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime_label_builder_status": self.regime_label_builder_status,
            "regime_label_builder_available": self.regime_label_builder_available,
            "regime_label_builder_used_in_training": self.regime_label_builder_used_in_training,
            "regime_specific_labeling_available": self.regime_specific_labeling_available,
            "regime_specific_training_applied": self.regime_specific_training_applied,
            "regime_label_config_used": dict(self.regime_label_config_used),
            "label_distribution_by_regime": {
                regime: dict(distribution)
                for regime, distribution in self.label_distribution_by_regime.items()
            },
            "missing_requirements": list(self.missing_requirements),
            "warnings": list(self.warnings),
            "reason": self.reason,
        }


class RegimeLabelBuilder:
    def __init__(
        self,
        *,
        planner: RegimeLabelConfigPlanner | None = None,
        direction_label_builder: DirectionLabelBuilder | None = None,
        tp_sl_label_builder: TpSlLabelBuilder | None = None,
    ) -> None:
        self._planner = planner or RegimeLabelConfigPlanner()
        self._direction_label_builder = direction_label_builder or DirectionLabelBuilder()
        self._tp_sl_label_builder = tp_sl_label_builder or TpSlLabelBuilder()

    def build(
        self,
        *,
        candles: list[Any],
        symbol: str,
        interval: str,
        feature_rows: list[Any],
        base_config: LabelConfig,
    ) -> RegimeLabelBuilderResult:
        planner_payload = self._planner.build_configs(base_label_config_id=base_config.label_version)
        configs = [dict(item) for item in planner_payload.get("configs", [])]
        configs_by_regime = {str(item["regime"]): item for item in configs}
        feature_map = {}
        for row in feature_rows:
            if isinstance(row, dict):
                candle_open_time = row.get("candle_open_time")
                features_json = dict(row.get("features_json", {}))
            else:
                candle_open_time = getattr(row, "candle_open_time", None)
                features_json = dict(getattr(row, "features_json", {}))
            feature_map[candle_open_time] = features_json
        missing_requirements: list[str] = []
        warnings: list[str] = []
        reason = None
        if not configs:
            missing_requirements.append("regime_specific_label_configs_unavailable")
            reason = "regime_label_configs_missing"
        if not feature_map:
            missing_requirements.append("regime_features_not_attached")
            reason = reason or "feature_rows_missing"
        if not candles:
            missing_requirements.append("market_data_missing_for_symbol")
            reason = reason or "candles_missing"

        if missing_requirements:
            return RegimeLabelBuilderResult(
                records=[],
                regime_label_builder_status="blocked",
                regime_label_builder_available=bool(configs),
                regime_label_builder_used_in_training=False,
                regime_specific_labeling_available=bool(configs),
                regime_specific_training_applied=False,
                regime_label_config_used={},
                label_distribution_by_regime={},
                missing_requirements=tuple(missing_requirements),
                warnings=tuple(warnings),
                reason=reason,
            )

        configured_horizons = {
            int(item.get("horizon", base_config.horizon_candles) or base_config.horizon_candles)
            for item in configs
        }
        if configured_horizons != {base_config.horizon_candles}:
            warnings.append("fixed_storage_horizon_enforced")

        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]
        closes = [float(candle.close) for candle in candles]
        atr_14 = TechnicalIndicators.atr(highs, lows, closes, 14)

        records: list[LabelRecord] = []
        label_distribution_by_regime: dict[str, Counter[str]] = defaultdict(Counter)
        regime_label_config_used: dict[str, str] = {}

        for index, candle in enumerate(candles):
            if index + base_config.horizon_candles >= len(candles):
                break

            atr_value = atr_14[index]
            current_close = closes[index]
            if atr_value is None or atr_value == 0 or current_close == 0:
                continue

            features_json = feature_map.get(candle.open_time)
            if not features_json:
                continue

            regime = self._resolve_regime(features_json)
            regime_config = configs_by_regime.get(regime) or configs_by_regime.get("unknown")
            if regime_config is None:
                continue
            regime_label_config_used.setdefault(regime, str(regime_config["config_id"]))

            future_window = candles[index + 1 : index + 1 + base_config.horizon_candles]
            future_close = float(future_window[-1].close)
            future_return = (future_close / current_close) - 1
            future_move_atr = (future_close - current_close) / atr_value

            up_move_atr = (max(float(future_candle.high) for future_candle in future_window) - current_close) / atr_value
            down_move_atr = (current_close - min(float(future_candle.low) for future_candle in future_window)) / atr_value

            effective_threshold = max(
                float(regime_config.get("threshold", base_config.direction_atr_threshold)),
                float(regime_config.get("flat_threshold", base_config.direction_atr_threshold)),
            )
            take_profit_atr = float(regime_config.get("take_profit_atr", base_config.take_profit_atr))
            stop_loss_atr = float(regime_config.get("stop_loss_atr", base_config.stop_loss_atr))

            direction_label = self._direction_label_builder.build(
                future_return=future_return,
                atr=atr_value,
                current_close=current_close,
                direction_atr_threshold=effective_threshold,
                flat_class_enabled=base_config.flat_class_enabled,
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

            record = LabelRecord(
                symbol=symbol,
                interval=interval,
                candle_open_time=candle.open_time,
                horizon_candles=base_config.horizon_candles,
                direction_label=direction_label,
                tp_before_sl=tp_before_sl,
                future_return=float(future_return),
                future_move_atr=float(future_move_atr),
                max_favorable_move_atr=float(max_favorable_move_atr),
                max_adverse_move_atr=float(max_adverse_move_atr),
                label_version=base_config.label_version,
            )
            records.append(record)
            label_distribution_by_regime[regime][direction_label] += 1

        if not records:
            missing_requirements.append("regime_runtime_labels_not_built")
            reason = reason or "runtime_label_records_missing"

        used_in_training = bool(records)
        return RegimeLabelBuilderResult(
            records=records,
            regime_label_builder_status="built" if used_in_training else "blocked",
            regime_label_builder_available=bool(configs),
            regime_label_builder_used_in_training=used_in_training,
            regime_specific_labeling_available=bool(configs),
            regime_specific_training_applied=used_in_training,
            regime_label_config_used=dict(regime_label_config_used),
            label_distribution_by_regime={
                regime: {
                    LABEL_UP: counts.get(LABEL_UP, 0),
                    LABEL_DOWN: counts.get(LABEL_DOWN, 0),
                    LABEL_FLAT: counts.get(LABEL_FLAT, 0),
                }
                for regime, counts in label_distribution_by_regime.items()
            },
            missing_requirements=tuple(missing_requirements),
            warnings=tuple(dict.fromkeys(warnings)),
            reason=reason,
        )

    @staticmethod
    def _resolve_regime(features_json: dict[str, Any]) -> str:
        ordered_regimes = (
            "trend_up",
            "trend_down",
            "range",
            "high_volatility",
            "low_volatility",
        )
        for regime in ordered_regimes:
            if float(features_json.get(f"regime_{regime}", 0.0) or 0.0) >= 0.5:
                return regime
        return "unknown"
