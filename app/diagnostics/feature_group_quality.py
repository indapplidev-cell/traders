from __future__ import annotations

from typing import Any


FEATURE_GROUP_QUALITY_NAME = "feature_group_quality"
FEATURE_GROUP_QUALITY_VERSION = "ml32"


class FeatureGroupQualityScorer:
    """Score coarse feature groups using lightweight name heuristics."""

    def analyze(
        self,
        rows: list[dict[str, Any]],
        *,
        label_key: str = "direction_label",
        features_key: str = "features_json",
    ) -> dict[str, Any]:
        feature_names = self._feature_names(rows, features_key)
        grouped_feature_names: dict[str, list[str]] = {}
        for feature_name in feature_names:
            grouped_feature_names.setdefault(self._group_name(feature_name), []).append(feature_name)

        groups: list[dict[str, Any]] = []
        weak_groups: list[str] = []
        strong_groups: list[str] = []
        for group_name, names in sorted(grouped_feature_names.items()):
            payload = self._group_payload(
                rows=rows,
                label_key=label_key,
                features_key=features_key,
                group_name=group_name,
                feature_names=names,
            )
            groups.append(payload)
            if payload["signal_score"] < 0.10 or payload["warnings"]:
                weak_groups.append(group_name)
            if payload["signal_score"] >= 0.25 and not payload["warnings"]:
                strong_groups.append(group_name)

        recommendations = self._recommendations(weak_groups=weak_groups, strong_groups=strong_groups)
        return {
            "group_name": FEATURE_GROUP_QUALITY_NAME,
            "group_version": FEATURE_GROUP_QUALITY_VERSION,
            "row_count": len(rows),
            "group_count": len(groups),
            "groups": groups,
            "weak_groups": weak_groups,
            "strong_groups": strong_groups,
            "recommendations": recommendations,
        }

    def _group_payload(
        self,
        *,
        rows: list[dict[str, Any]],
        label_key: str,
        features_key: str,
        group_name: str,
        feature_names: list[str],
    ) -> dict[str, Any]:
        row_count = len(rows)
        missing_values = 0
        constant_feature_count = 0
        low_variance_feature_count = 0
        signal_scores: list[float] = []

        for feature_name in feature_names:
            values = [self._feature_value(row, features_key, feature_name) for row in rows]
            missing_values += sum(int(value is None) for value in values)
            non_null_values = [float(value) for value in values if value is not None]
            if non_null_values and max(non_null_values) == min(non_null_values):
                constant_feature_count += 1
            variance = self._variance(non_null_values)
            if variance is not None and variance <= 1e-6:
                low_variance_feature_count += 1
            signal_scores.append(
                self._class_separation(
                    rows=rows,
                    feature_name=feature_name,
                    label_key=label_key,
                    features_key=features_key,
                )
            )

        denominator = row_count * len(feature_names)
        missing_rate = (missing_values / denominator) if denominator > 0 else 0.0
        base_signal = (sum(signal_scores) / len(signal_scores)) if signal_scores else 0.0
        penalty = (
            constant_feature_count * 0.02
            + low_variance_feature_count * 0.02
            + (0.10 if missing_rate >= 0.20 else 0.0)
        )
        signal_score = max(base_signal - penalty, 0.0)
        warnings: list[str] = []
        if missing_rate >= 0.20:
            warnings.append("high_missing_rate")
        if constant_feature_count > 0:
            warnings.append("constant_features_detected")
        if low_variance_feature_count > 0:
            warnings.append("low_variance_features_detected")
        if signal_score < 0.10:
            warnings.append("weak_signal_detected")

        return {
            "group_name": group_name,
            "feature_count": len(feature_names),
            "missing_rate": round(missing_rate, 6),
            "constant_feature_count": constant_feature_count,
            "low_variance_feature_count": low_variance_feature_count,
            "signal_score": round(signal_score, 6),
            "warnings": warnings,
            "recommendations": self._group_recommendations(group_name=group_name, warnings=warnings),
        }

    @staticmethod
    def _feature_names(rows: list[dict[str, Any]], features_key: str) -> list[str]:
        names: set[str] = set()
        for row in rows:
            for feature_name in dict(row.get(features_key, {})).keys():
                names.add(str(feature_name))
        return sorted(names)

    @staticmethod
    def _feature_value(row: dict[str, Any], features_key: str, feature_name: str) -> Any:
        return dict(row.get(features_key, {})).get(feature_name)

    @staticmethod
    def _variance(values: list[float]) -> float | None:
        if not values:
            return None
        mean = sum(values) / len(values)
        return sum((value - mean) ** 2 for value in values) / len(values)

    def _class_separation(
        self,
        *,
        rows: list[dict[str, Any]],
        feature_name: str,
        label_key: str,
        features_key: str,
    ) -> float:
        buckets: dict[str, list[float]] = {}
        for row in rows:
            value = self._feature_value(row, features_key, feature_name)
            if value is None:
                continue
            label = str(row.get(label_key, "UNKNOWN"))
            buckets.setdefault(label, []).append(float(value))
        means = [
            sum(values) / len(values)
            for values in buckets.values()
            if values
        ]
        if len(means) < 2:
            return 0.0
        return max(means) - min(means)

    @staticmethod
    def _group_name(feature_name: str) -> str:
        normalized = feature_name.lower()
        if normalized.startswith("regime_"):
            return "regime"
        if any(token in normalized for token in ("volume", "taker_buy")):
            return "volume"
        if any(token in normalized for token in ("atr", "volatility")):
            return "volatility"
        if any(token in normalized for token in ("ema", "trend", "slope", "pullback", "close_above")):
            return "trend"
        if any(token in normalized for token in ("rsi", "macd", "return", "log_return")):
            return "momentum"
        if any(token in normalized for token in ("body", "wick", "range", "close_position")):
            return "price_action"
        return "unknown"

    @staticmethod
    def _group_recommendations(*, group_name: str, warnings: list[str]) -> list[str]:
        recommendations: list[str] = []
        if "high_missing_rate" in warnings:
            recommendations.append(f"Reduce missingness in the {group_name} feature group.")
        if "constant_features_detected" in warnings:
            recommendations.append(f"Remove constant features from the {group_name} group.")
        if "low_variance_features_detected" in warnings:
            recommendations.append(f"Down-rank low-variance features in the {group_name} group.")
        if "weak_signal_detected" in warnings:
            recommendations.append(f"Rework the {group_name} feature group because directional separation is weak.")
        if not recommendations:
            recommendations.append(f"The {group_name} feature group looks usable for research.")
        return recommendations

    @staticmethod
    def _recommendations(*, weak_groups: list[str], strong_groups: list[str]) -> list[str]:
        recommendations: list[str] = []
        if weak_groups:
            recommendations.append(
                "Investigate weak feature groups first: " + ", ".join(sorted(weak_groups))
            )
        if strong_groups:
            recommendations.append(
                "Preserve the strongest feature groups in the next experiment: " + ", ".join(sorted(strong_groups))
            )
        if not recommendations:
            recommendations.append("Feature groups look balanced enough for the next research cycle.")
        return recommendations
