from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ENTRY_PATH_QUALITY_FILTER_NAME = "entry_path_quality_filter"
ENTRY_PATH_QUALITY_FILTER_VERSION = "ml38.10.16"
ENTRY_PATH_SCORE_PROFILE_LEGACY = "legacy_balanced_v1"
ENTRY_PATH_SCORE_PROFILE_DIRECTIONAL_CONTEXT_V2 = "directional_context_v2"
ENTRY_PATH_SCORE_PROFILE_MAE_AWARE_RR_V3 = "mae_aware_rr_v3"


@dataclass(frozen=True, slots=True)
class EntryPathQualityScores:
    entry_path_quality_score: float
    stop_pressure_risk_score: float
    risk_reward_quality_score: float
    chop_risk_score: float
    trap_risk_score: float
    direction_alignment_score: float = 0.0
    direction_opposition_risk_score: float = 0.0
    wick_pressure_risk_score: float = 0.0
    exhaustion_risk_score: float = 0.0
    stop_pressure_effectiveness_filter_score: float = 0.0
    mae_pressure_risk_score: float = 0.0
    rr_adjusted_entry_score: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "entry_path_quality_score": float(self.entry_path_quality_score),
            "stop_pressure_risk_score": float(self.stop_pressure_risk_score),
            "risk_reward_quality_score": float(self.risk_reward_quality_score),
            "chop_risk_score": float(self.chop_risk_score),
            "trap_risk_score": float(self.trap_risk_score),
            "direction_alignment_score": float(self.direction_alignment_score),
            "direction_opposition_risk_score": float(self.direction_opposition_risk_score),
            "wick_pressure_risk_score": float(self.wick_pressure_risk_score),
            "exhaustion_risk_score": float(self.exhaustion_risk_score),
            "stop_pressure_effectiveness_filter_score": float(self.stop_pressure_effectiveness_filter_score),
            "mae_pressure_risk_score": float(self.mae_pressure_risk_score),
            "rr_adjusted_entry_score": float(self.rr_adjusted_entry_score),
        }


class EntryPathQualityFilter:
    """Ex-ante entry quality scoring for two-stage trade decisions.

    This module must not use future candles or realized MAE/MFE to decide whether
    a prediction is tradable. It uses only setup payload and current feature rows.
    Realized MAE/MFE belongs to diagnostics outside this class.
    """

    def score_rows(
        self,
        *,
        feature_names: list[str] | tuple[str, ...],
        feature_rows: list[list[float]] | tuple[list[float], ...],
        setup_quality_scores: list[float],
        expected_move_atr: list[float],
        invalidation_distance_atr: list[float],
        predicted_labels: list[str] | tuple[str, ...] | None = None,
        score_profile: str | None = None,
    ) -> dict[str, Any]:
        row_count = max(
            len(setup_quality_scores),
            len(expected_move_atr),
            len(invalidation_distance_atr),
            len(feature_rows),
            len(predicted_labels or ()),
        )
        feature_index = {name: index for index, name in enumerate(feature_names)}
        profile = str(score_profile or ENTRY_PATH_SCORE_PROFILE_LEGACY)
        score_rows: list[dict[str, float]] = []
        entry_scores: list[float] = []
        stop_scores: list[float] = []
        rr_scores: list[float] = []
        chop_scores: list[float] = []
        trap_scores: list[float] = []
        alignment_scores: list[float] = []
        opposition_scores: list[float] = []
        wick_scores: list[float] = []
        exhaustion_scores: list[float] = []
        effectiveness_scores: list[float] = []
        mae_pressure_scores: list[float] = []
        rr_adjusted_scores: list[float] = []

        for index in range(row_count):
            features = list(feature_rows[index]) if index < len(feature_rows) else []
            predicted_label = self._label_value(predicted_labels, index)
            setup_quality = self._bounded(self._list_value(setup_quality_scores, index, 0.0))
            expected_move = abs(self._list_value(expected_move_atr, index, 0.0))
            invalidation_distance = abs(self._list_value(invalidation_distance_atr, index, 0.0))

            risk_reward_quality = self._risk_reward_quality(
                expected_move_atr=expected_move,
                invalidation_distance_atr=invalidation_distance,
            )
            chop_risk = self._chop_risk(feature_index=feature_index, features=features)
            trap_risk = self._trap_risk(feature_index=feature_index, features=features)

            if profile in {
                ENTRY_PATH_SCORE_PROFILE_DIRECTIONAL_CONTEXT_V2,
                ENTRY_PATH_SCORE_PROFILE_MAE_AWARE_RR_V3,
            }:
                directional_context = self._directional_context(
                    feature_index=feature_index,
                    features=features,
                    predicted_label=predicted_label,
                )
                direction_alignment = directional_context["direction_alignment_score"]
                direction_opposition = directional_context["direction_opposition_risk_score"]
                wick_pressure = directional_context["wick_pressure_risk_score"]
                exhaustion_risk = directional_context["exhaustion_risk_score"]
                followthrough = directional_context["expected_followthrough_score"]
                invalidation_quality = directional_context["invalidation_quality_score"]

                adjusted_rr_quality = self._bounded(
                    0.78 * risk_reward_quality
                    + 0.12 * invalidation_quality
                    + 0.10 * followthrough
                )
                stop_pressure_risk = self._bounded(
                    0.30 * (1.0 - adjusted_rr_quality)
                    + 0.18 * (1.0 - setup_quality)
                    + 0.16 * chop_risk
                    + 0.15 * trap_risk
                    + 0.13 * direction_opposition
                    + 0.05 * wick_pressure
                    + 0.03 * exhaustion_risk
                    - 0.10 * direction_alignment
                )
                entry_quality = self._bounded(
                    0.30 * setup_quality
                    + 0.25 * adjusted_rr_quality
                    + 0.20 * direction_alignment
                    + 0.10 * followthrough
                    + 0.08 * (1.0 - chop_risk)
                    + 0.07 * (1.0 - trap_risk)
                )
                mae_pressure_risk = self._bounded(
                    0.24 * chop_risk
                    + 0.20 * trap_risk
                    + 0.18 * direction_opposition
                    + 0.16 * wick_pressure
                    + 0.12 * exhaustion_risk
                    + 0.10 * (1.0 - invalidation_quality)
                    - 0.08 * direction_alignment
                )
                rr_adjusted_entry_score = self._bounded(
                    0.44 * entry_quality
                    + 0.24 * adjusted_rr_quality
                    + 0.18 * (1.0 - mae_pressure_risk)
                    + 0.14 * followthrough
                )
                if profile == ENTRY_PATH_SCORE_PROFILE_MAE_AWARE_RR_V3:
                    stop_pressure_risk = self._bounded(
                        0.58 * stop_pressure_risk
                        + 0.32 * mae_pressure_risk
                        + 0.10 * (1.0 - rr_adjusted_entry_score)
                    )
                    entry_quality = self._bounded(
                        0.62 * entry_quality
                        + 0.26 * rr_adjusted_entry_score
                        + 0.12 * (1.0 - mae_pressure_risk)
                    )
                stop_pressure_effectiveness_filter_score = self._bounded(
                    0.45 * stop_pressure_risk
                    + 0.25 * mae_pressure_risk
                    + 0.15 * direction_opposition
                    + 0.10 * wick_pressure
                    + 0.05 * exhaustion_risk
                )
                risk_reward_quality = adjusted_rr_quality
            else:
                direction_alignment = 0.0
                direction_opposition = 0.0
                wick_pressure = 0.0
                exhaustion_risk = 0.0
                stop_pressure_risk = self._bounded(
                    0.45 * (1.0 - risk_reward_quality)
                    + 0.25 * (1.0 - setup_quality)
                    + 0.20 * chop_risk
                    + 0.10 * trap_risk
                )
                entry_quality = self._bounded(
                    0.45 * setup_quality
                    + 0.35 * risk_reward_quality
                    + 0.10 * (1.0 - chop_risk)
                    + 0.10 * (1.0 - trap_risk)
                )
                stop_pressure_effectiveness_filter_score = stop_pressure_risk
                mae_pressure_risk = stop_pressure_risk
                rr_adjusted_entry_score = entry_quality

            score = EntryPathQualityScores(
                entry_path_quality_score=entry_quality,
                stop_pressure_risk_score=stop_pressure_risk,
                risk_reward_quality_score=risk_reward_quality,
                chop_risk_score=chop_risk,
                trap_risk_score=trap_risk,
                direction_alignment_score=direction_alignment,
                direction_opposition_risk_score=direction_opposition,
                wick_pressure_risk_score=wick_pressure,
                exhaustion_risk_score=exhaustion_risk,
                stop_pressure_effectiveness_filter_score=stop_pressure_effectiveness_filter_score,
                mae_pressure_risk_score=mae_pressure_risk,
                rr_adjusted_entry_score=rr_adjusted_entry_score,
            )
            payload = score.to_dict()
            score_rows.append(payload)
            entry_scores.append(payload["entry_path_quality_score"])
            stop_scores.append(payload["stop_pressure_risk_score"])
            rr_scores.append(payload["risk_reward_quality_score"])
            chop_scores.append(payload["chop_risk_score"])
            trap_scores.append(payload["trap_risk_score"])
            alignment_scores.append(payload["direction_alignment_score"])
            opposition_scores.append(payload["direction_opposition_risk_score"])
            wick_scores.append(payload["wick_pressure_risk_score"])
            exhaustion_scores.append(payload["exhaustion_risk_score"])
            effectiveness_scores.append(payload["stop_pressure_effectiveness_filter_score"])
            mae_pressure_scores.append(payload["mae_pressure_risk_score"])
            rr_adjusted_scores.append(payload["rr_adjusted_entry_score"])

        return {
            "diagnostic_name": ENTRY_PATH_QUALITY_FILTER_NAME,
            "diagnostic_version": ENTRY_PATH_QUALITY_FILTER_VERSION,
            "score_profile": profile,
            "row_count": int(row_count),
            "entry_path_quality_scores": entry_scores,
            "stop_pressure_risk_scores": stop_scores,
            "risk_reward_quality_scores": rr_scores,
            "chop_risk_scores": chop_scores,
            "trap_risk_scores": trap_scores,
            "direction_alignment_scores": alignment_scores,
            "direction_opposition_risk_scores": opposition_scores,
            "wick_pressure_risk_scores": wick_scores,
            "exhaustion_risk_scores": exhaustion_scores,
            "stop_pressure_effectiveness_filter_scores": effectiveness_scores,
            "mae_pressure_risk_scores": mae_pressure_scores,
            "rr_adjusted_entry_scores": rr_adjusted_scores,
            "score_rows": score_rows,
            "summary": {
                "avg_entry_path_quality_score": self._mean(entry_scores),
                "avg_stop_pressure_risk_score": self._mean(stop_scores),
                "avg_risk_reward_quality_score": self._mean(rr_scores),
                "avg_chop_risk_score": self._mean(chop_scores),
                "avg_trap_risk_score": self._mean(trap_scores),
                "avg_direction_alignment_score": self._mean(alignment_scores),
                "avg_direction_opposition_risk_score": self._mean(opposition_scores),
                "avg_wick_pressure_risk_score": self._mean(wick_scores),
                "avg_exhaustion_risk_score": self._mean(exhaustion_scores),
                "avg_stop_pressure_effectiveness_filter_score": self._mean(effectiveness_scores),
                "avg_mae_pressure_risk_score": self._mean(mae_pressure_scores),
                "avg_rr_adjusted_entry_score": self._mean(rr_adjusted_scores),
                "low_entry_quality_row_count": sum(int(value < 0.60) for value in entry_scores),
                "high_stop_pressure_row_count": sum(int(value > 0.55) for value in stop_scores),
            },
            "safety": {
                "uses_future_candles_for_filter": False,
                "uses_realized_mae_mfe_for_filter": False,
                "uses_only_ex_ante_setup_and_feature_context": True,
            },
        }

    @staticmethod
    def _list_value(values: list[float], index: int, default: float) -> float:
        if index >= len(values):
            return float(default)
        try:
            return float(values[index])
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _label_value(values: list[str] | tuple[str, ...] | None, index: int) -> str:
        if not values or index >= len(values):
            return ""
        return str(values[index] or "").upper()

    @classmethod
    def _feature_value(
        cls,
        *,
        feature_index: dict[str, int],
        features: list[float],
        names: tuple[str, ...],
        default: float = 0.0,
    ) -> float:
        for name in names:
            index = feature_index.get(name)
            if index is None or index >= len(features):
                continue
            try:
                return float(features[index])
            except (TypeError, ValueError):
                continue
        return float(default)

    @classmethod
    def _chop_risk(cls, *, feature_index: dict[str, int], features: list[float]) -> float:
        values = [
            cls._feature_value(
                feature_index=feature_index,
                features=features,
                names=("alt_no_trade_chop_score", "no_trade_chop_score"),
            ),
            cls._feature_value(
                feature_index=feature_index,
                features=features,
                names=("alt_range_chop_score", "range_chop_score"),
            ),
            cls._feature_value(
                feature_index=feature_index,
                features=features,
                names=("path_16_chop_score",),
            ),
            cls._feature_value(
                feature_index=feature_index,
                features=features,
                names=("bollinger_squeeze_score",),
            ) * 0.35,
        ]
        return cls._bounded(max(values) if values else 0.0)

    @classmethod
    def _trap_risk(cls, *, feature_index: dict[str, int], features: list[float]) -> float:
        false_breakout = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=(
                "schwager_false_breakout_risk_score",
                "alt_false_breakout_risk_score",
                "false_breakout_risk_score",
            ),
        )
        bull_trap = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("schwager_bull_trap_risk_score", "bull_trap_risk_score"),
        )
        bear_trap = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("schwager_bear_trap_risk_score", "bear_trap_risk_score"),
        )
        failed_return = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("schwager_failed_breakout_return_inside_range_score",),
        )
        stop_hunt = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("schwager_stop_hunt_like_move_score",),
        )
        trap_safe = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("schwager_trap_safe_setup_score", "trap_safe_setup_score"),
        )
        raw = max(false_breakout, bull_trap, bear_trap, failed_return, stop_hunt, 0.0)
        if trap_safe > 0.0:
            raw = max(0.0, raw - 0.35 * trap_safe)
        return cls._bounded(raw)

    @classmethod
    def _directional_context(
        cls,
        *,
        feature_index: dict[str, int],
        features: list[float],
        predicted_label: str,
    ) -> dict[str, float]:
        followthrough = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("nison_expected_followthrough_score",),
        )
        invalidation_quality = cls._feature_value(
            feature_index=feature_index,
            features=features,
            names=("schwager_invalidation_quality_score",),
        )
        if predicted_label == "UP":
            alignment = max(
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_trend_continuation_long_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_pullback_long_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_support_retest_long_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_breakout_long_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_indicator_confluence_long_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("nison_pattern_at_support_score",)),
                followthrough,
            )
            opposition = max(
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_trend_exhaustion_long_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("schwager_bull_trap_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("schwager_spike_high_retest_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("nison_shooting_star_after_advance_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("nison_pattern_at_resistance_score",)),
            )
            wick_pressure = cls._feature_value(
                feature_index=feature_index,
                features=features,
                names=("path_12_upper_wick_pressure",),
            )
            exhaustion = max(
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_trend_exhaustion_long_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("volume_16_exhaustion_score",)),
            )
        elif predicted_label == "DOWN":
            alignment = max(
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_trend_continuation_short_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_pullback_short_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_resistance_rejection_short_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_breakdown_short_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_indicator_confluence_short_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("nison_pattern_at_resistance_score",)),
                followthrough,
            )
            opposition = max(
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_trend_exhaustion_short_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("schwager_bear_trap_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("schwager_spike_low_retest_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("nison_hammer_after_decline_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("nison_pattern_at_support_score",)),
            )
            wick_pressure = cls._feature_value(
                feature_index=feature_index,
                features=features,
                names=("path_12_lower_wick_pressure",),
            )
            exhaustion = max(
                cls._feature_value(feature_index=feature_index, features=features, names=("alt_trend_exhaustion_short_risk_score",)),
                cls._feature_value(feature_index=feature_index, features=features, names=("volume_16_exhaustion_score",)),
            )
        else:
            alignment = 0.0
            opposition = 0.0
            wick_pressure = 0.0
            exhaustion = 0.0

        if invalidation_quality > 0.0:
            opposition = max(0.0, opposition - 0.20 * invalidation_quality)
            wick_pressure = max(0.0, wick_pressure - 0.10 * invalidation_quality)

        return {
            "direction_alignment_score": cls._bounded(alignment),
            "direction_opposition_risk_score": cls._bounded(opposition),
            "wick_pressure_risk_score": cls._bounded(wick_pressure),
            "exhaustion_risk_score": cls._bounded(exhaustion),
            "expected_followthrough_score": cls._bounded(followthrough),
            "invalidation_quality_score": cls._bounded(invalidation_quality),
        }

    @classmethod
    def _risk_reward_quality(
        cls,
        *,
        expected_move_atr: float,
        invalidation_distance_atr: float,
    ) -> float:
        expected_move = abs(float(expected_move_atr or 0.0))
        invalidation_distance = abs(float(invalidation_distance_atr or 0.0))
        if expected_move <= 0.0 and invalidation_distance <= 0.0:
            return 0.0
        if invalidation_distance <= 1e-9:
            return 1.0 if expected_move > 0.0 else 0.0
        ratio = expected_move / invalidation_distance
        return cls._bounded(ratio / 2.0)

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _mean(values: list[float]) -> float:
        return float(sum(values) / len(values)) if values else 0.0
