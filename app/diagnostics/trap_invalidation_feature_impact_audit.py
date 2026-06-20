from __future__ import annotations

from statistics import mean, median
from typing import Any, Sequence

from app.features.feature_models import SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES


class TrapInvalidationFeatureImpactAudit:
    """Audit whether Schwager trap/invalidation features separate TP/FP trade decisions.

    This audit is intentionally diagnostic-only. It must not approve a model,
    activate a model, or change live-trading behavior.
    """

    DIAGNOSTIC_NAME = "trap_invalidation_feature_impact_audit"
    DIAGNOSTIC_VERSION = "ml38.10.11"

    RISK_FEATURE_HINTS = (
        "risk",
        "trap",
        "failed_breakout",
        "stop_hunt",
        "range_reentry",
    )
    QUALITY_FEATURE_HINTS = (
        "quality",
        "safe",
    )

    def analyze(
        self,
        *,
        feature_names: Sequence[str],
        feature_rows: Sequence[Sequence[float]],
        opportunity_probabilities: Sequence[float],
        opportunity_targets: Sequence[int],
        direction_targets: Sequence[int],
        direction_probabilities: Sequence[Sequence[float]],
        setup_quality_scores: Sequence[float] | None = None,
        opportunity_probability_threshold: float = 0.5,
        setup_quality_decision_mask_enabled: bool = False,
        setup_quality_decision_mask_min_threshold: float | None = None,
    ) -> dict[str, Any]:
        feature_names_list = [str(item) for item in feature_names]
        feature_index = {name: index for index, name in enumerate(feature_names_list)}
        trap_features = [
            name
            for name in SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES
            if name in feature_index
        ]
        row_count = min(
            len(feature_rows),
            len(opportunity_probabilities),
            len(opportunity_targets),
            len(direction_targets),
            len(direction_probabilities),
        )
        setup_quality = list(setup_quality_scores or [])
        if len(setup_quality) < row_count:
            setup_quality.extend([0.0] * (row_count - len(setup_quality)))

        if row_count <= 0 or not trap_features:
            return {
                "diagnostic_name": self.DIAGNOSTIC_NAME,
                "diagnostic_version": self.DIAGNOSTIC_VERSION,
                "row_count": int(row_count),
                "trap_feature_count": int(len(trap_features)),
                "audit_status": "SKIPPED",
                "skip_reason": "no_rows_or_no_trap_features",
                "feature_names": list(trap_features),
                "feature_impact_status": "UNKNOWN",
                "recommendation": "run_training_with_fv4_trap_features_before_using_this_audit",
            }

        threshold = float(opportunity_probability_threshold)
        raw_predicted_trade_flags = [
            int(float(opportunity_probabilities[index]) >= threshold)
            for index in range(row_count)
        ]
        masked_predicted_trade_flags = self._apply_setup_quality_mask(
            raw_predicted_trade_flags=raw_predicted_trade_flags,
            setup_quality_scores=setup_quality,
            setup_quality_decision_mask_enabled=setup_quality_decision_mask_enabled,
            setup_quality_decision_mask_min_threshold=setup_quality_decision_mask_min_threshold,
        )
        actual_trade_flags = [int(float(opportunity_targets[index]) >= 0.5) for index in range(row_count)]

        row_groups = self._build_row_groups(
            predicted_trade_flags=masked_predicted_trade_flags,
            actual_trade_flags=actual_trade_flags,
            setup_quality_scores=setup_quality,
        )
        feature_impacts = {
            feature_name: self._feature_impact(
                feature_name=feature_name,
                feature_index=feature_index[feature_name],
                feature_rows=feature_rows,
                row_groups=row_groups,
            )
            for feature_name in trap_features
        }
        top_separating_features = sorted(
            (
                {
                    "feature_name": feature_name,
                    "tp_mean": payload["true_positive"].get("mean"),
                    "fp_mean": payload["false_positive"].get("mean"),
                    "fp_minus_tp_mean": payload.get("false_positive_minus_true_positive_mean"),
                    "abs_fp_tp_separation": payload.get("abs_fp_tp_separation"),
                    "impact_direction": payload.get("impact_direction"),
                }
                for feature_name, payload in feature_impacts.items()
            ),
            key=lambda item: float(item.get("abs_fp_tp_separation") or 0.0),
            reverse=True,
        )
        max_abs_separation = float(
            top_separating_features[0].get("abs_fp_tp_separation") or 0.0
        ) if top_separating_features else 0.0
        average_abs_separation = (
            mean(float(item.get("abs_fp_tp_separation") or 0.0) for item in top_separating_features)
            if top_separating_features
            else 0.0
        )
        tp_count = len(row_groups["true_positive"])
        fp_count = len(row_groups["false_positive"])
        strong_tp_count = len(row_groups["strong_setup_true_positive"])
        strong_fp_count = len(row_groups["strong_setup_false_positive"])
        feature_impact_status = self._impact_status(
            tp_count=tp_count,
            fp_count=fp_count,
            max_abs_separation=max_abs_separation,
            average_abs_separation=average_abs_separation,
        )

        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "row_count": int(row_count),
            "trap_feature_count": int(len(trap_features)),
            "feature_names": list(trap_features),
            "audit_status": "COMPLETED",
            "feature_impact_status": feature_impact_status,
            "opportunity_probability_threshold": threshold,
            "setup_quality_decision_mask_enabled": bool(setup_quality_decision_mask_enabled),
            "setup_quality_decision_mask_min_threshold": setup_quality_decision_mask_min_threshold,
            "group_counts": {name: len(indexes) for name, indexes in row_groups.items()},
            "true_positive_count": tp_count,
            "false_positive_count": fp_count,
            "false_negative_count": len(row_groups["false_negative"]),
            "true_negative_count": len(row_groups["true_negative"]),
            "strong_setup_true_positive_count": strong_tp_count,
            "strong_setup_false_positive_count": strong_fp_count,
            "max_abs_fp_tp_separation": max_abs_separation,
            "average_abs_fp_tp_separation": average_abs_separation,
            "top_separating_features": top_separating_features[:10],
            "feature_impacts": feature_impacts,
            "recommendation": self._recommendation(
                feature_impact_status=feature_impact_status,
                strong_fp_count=strong_fp_count,
                max_abs_separation=max_abs_separation,
            ),
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    @classmethod
    def _apply_setup_quality_mask(
        cls,
        *,
        raw_predicted_trade_flags: Sequence[int],
        setup_quality_scores: Sequence[float],
        setup_quality_decision_mask_enabled: bool,
        setup_quality_decision_mask_min_threshold: float | None,
    ) -> list[int]:
        if not setup_quality_decision_mask_enabled:
            return [int(value) for value in raw_predicted_trade_flags]
        threshold = 0.0 if setup_quality_decision_mask_min_threshold is None else float(setup_quality_decision_mask_min_threshold)
        masked: list[int] = []
        for index, raw_flag in enumerate(raw_predicted_trade_flags):
            quality = float(setup_quality_scores[index] if index < len(setup_quality_scores) else 0.0)
            if quality < threshold:
                masked.append(0)
            else:
                masked.append(int(raw_flag))
        return masked

    @classmethod
    def _build_row_groups(
        cls,
        *,
        predicted_trade_flags: Sequence[int],
        actual_trade_flags: Sequence[int],
        setup_quality_scores: Sequence[float],
    ) -> dict[str, list[int]]:
        groups: dict[str, list[int]] = {
            "true_positive": [],
            "false_positive": [],
            "false_negative": [],
            "true_negative": [],
            "predicted_trade": [],
            "actual_trade": [],
            "strong_setup_true_positive": [],
            "strong_setup_false_positive": [],
        }
        for index, (predicted, actual) in enumerate(zip(predicted_trade_flags, actual_trade_flags)):
            predicted_trade = int(predicted) == 1
            actual_trade = int(actual) == 1
            setup_quality = float(setup_quality_scores[index] if index < len(setup_quality_scores) else 0.0)
            if predicted_trade:
                groups["predicted_trade"].append(index)
            if actual_trade:
                groups["actual_trade"].append(index)
            if predicted_trade and actual_trade:
                groups["true_positive"].append(index)
                if setup_quality >= 0.75:
                    groups["strong_setup_true_positive"].append(index)
            elif predicted_trade and not actual_trade:
                groups["false_positive"].append(index)
                if setup_quality >= 0.75:
                    groups["strong_setup_false_positive"].append(index)
            elif not predicted_trade and actual_trade:
                groups["false_negative"].append(index)
            else:
                groups["true_negative"].append(index)
        return groups

    @classmethod
    def _feature_impact(
        cls,
        *,
        feature_name: str,
        feature_index: int,
        feature_rows: Sequence[Sequence[float]],
        row_groups: dict[str, list[int]],
    ) -> dict[str, Any]:
        summaries = {
            group_name: cls._summary(
                cls._values(feature_rows=feature_rows, feature_index=feature_index, row_indexes=row_indexes)
            )
            for group_name, row_indexes in row_groups.items()
        }
        tp_mean = summaries["true_positive"].get("mean")
        fp_mean = summaries["false_positive"].get("mean")
        if tp_mean is None or fp_mean is None:
            diff = None
            abs_diff = 0.0
        else:
            diff = float(fp_mean) - float(tp_mean)
            abs_diff = abs(diff)
        return {
            **summaries,
            "false_positive_minus_true_positive_mean": diff,
            "abs_fp_tp_separation": abs_diff,
            "impact_direction": cls._impact_direction(feature_name=feature_name, diff=diff),
        }

    @staticmethod
    def _values(
        *,
        feature_rows: Sequence[Sequence[float]],
        feature_index: int,
        row_indexes: Sequence[int],
    ) -> list[float]:
        values: list[float] = []
        for row_index in row_indexes:
            if row_index >= len(feature_rows):
                continue
            row = feature_rows[row_index]
            if feature_index >= len(row):
                continue
            try:
                values.append(float(row[feature_index]))
            except (TypeError, ValueError):
                values.append(0.0)
        return values

    @staticmethod
    def _summary(values: Sequence[float]) -> dict[str, Any]:
        clean = [float(value) for value in values]
        if not clean:
            return {
                "count": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "std": None,
            }
        avg = mean(clean)
        variance = mean([(value - avg) ** 2 for value in clean]) if len(clean) > 1 else 0.0
        return {
            "count": len(clean),
            "mean": avg,
            "median": median(clean),
            "min": min(clean),
            "max": max(clean),
            "std": variance ** 0.5,
        }

    @classmethod
    def _impact_direction(cls, *, feature_name: str, diff: float | None) -> str:
        if diff is None:
            return "unknown"
        name = feature_name.lower()
        is_quality = any(token in name for token in cls.QUALITY_FEATURE_HINTS)
        is_risk = any(token in name for token in cls.RISK_FEATURE_HINTS)
        if is_quality:
            if diff < 0:
                return "expected_quality_higher_on_true_positive"
            return "unexpected_quality_higher_on_false_positive"
        if is_risk:
            if diff > 0:
                return "expected_risk_higher_on_false_positive"
            return "unexpected_risk_higher_on_true_positive"
        return "neutral"

    @staticmethod
    def _impact_status(
        *,
        tp_count: int,
        fp_count: int,
        max_abs_separation: float,
        average_abs_separation: float,
    ) -> str:
        if tp_count < 10 or fp_count < 10:
            return "INSUFFICIENT_ROWS"
        if max_abs_separation >= 0.08 and average_abs_separation >= 0.025:
            return "USEFUL"
        if max_abs_separation >= 0.04:
            return "WEAK_BUT_PRESENT"
        return "NO_CLEAR_IMPACT"

    @staticmethod
    def _recommendation(
        *,
        feature_impact_status: str,
        strong_fp_count: int,
        max_abs_separation: float,
    ) -> str:
        if feature_impact_status == "USEFUL" and strong_fp_count > 0:
            return "consider_trap_risk_decision_penalty_or_mask"
        if feature_impact_status == "WEAK_BUT_PRESENT":
            return "inspect_top_separating_features_before_adding_penalty"
        if feature_impact_status == "INSUFFICIENT_ROWS":
            return "run_quick_quality_on_more_symbols_before_deciding"
        if max_abs_separation < 0.04:
            return "rewrite_or_strengthen_trap_feature_formulas_before_more_tuning"
        return "keep_as_diagnostic_only"
