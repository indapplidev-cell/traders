from __future__ import annotations

from collections import Counter
from typing import Any

from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer


FEATURE_QUALITY_DIAGNOSTIC_NAME = "feature_quality_diagnostics"
FEATURE_QUALITY_DIAGNOSTIC_VERSION = "ml30"


class FeatureQualityDiagnostics:
    """Measure whether a feature matrix has enough signal to resist collapse."""

    def __init__(
        self,
        *,
        feature_group_scorer: FeatureGroupQualityScorer | None = None,
    ) -> None:
        self._feature_group_scorer = feature_group_scorer or FeatureGroupQualityScorer()

    def analyze(
        self,
        rows: list[dict[str, Any]],
        *,
        label_key: str = "direction_label",
        features_key: str = "features_json",
    ) -> dict[str, Any]:
        feature_names = self._feature_names(rows, features_key)
        row_count = len(rows)
        label_distribution = self._label_distribution(rows, label_key)
        missing_value_summary: dict[str, int] = {}
        constant_features: list[str] = []
        high_missing_features: list[str] = []
        low_variance_features: list[str] = []
        scored_features: list[dict[str, Any]] = []

        for feature_name in feature_names:
            values = [self._feature_value(row, features_key, feature_name) for row in rows]
            missing_count = sum(int(value is None) for value in values)
            missing_value_summary[feature_name] = missing_count
            non_null_values = [float(value) for value in values if value is not None]
            variance = self._variance(non_null_values)
            if non_null_values and max(non_null_values) == min(non_null_values):
                constant_features.append(feature_name)
            if row_count > 0 and (missing_count / row_count) >= 0.20:
                high_missing_features.append(feature_name)
            if variance is not None and variance <= 1e-6:
                low_variance_features.append(feature_name)
            separation_score = self._class_separation(
                rows=rows,
                feature_name=feature_name,
                label_key=label_key,
                features_key=features_key,
            )
            scored_features.append(
                {
                    "feature_name": feature_name,
                    "separation_score": separation_score,
                    "missing_count": missing_count,
                    "variance": None if variance is None else round(float(variance), 8),
                }
            )

        scored_features.sort(
            key=lambda item: (float(item["separation_score"] or 0.0), -item["missing_count"]),
            reverse=True,
        )
        feature_signal_score = self._feature_signal_score(
            scored_features=scored_features,
            constant_feature_count=len(constant_features),
            high_missing_feature_count=len(high_missing_features),
            low_variance_feature_count=len(low_variance_features),
        )
        weak_feature_warnings = []
        if constant_features:
            weak_feature_warnings.append("constant_features_detected")
        if high_missing_features:
            weak_feature_warnings.append("high_missing_features_detected")
        if low_variance_features:
            weak_feature_warnings.append("low_variance_features_detected")
        if feature_signal_score < 0.10:
            weak_feature_warnings.append("feature_signal_score_too_low")
        feature_group_summary = self._feature_group_scorer.analyze(
            rows,
            label_key=label_key,
            features_key=features_key,
        )
        weak_signal_detected = bool(
            "feature_signal_score_too_low" in weak_feature_warnings
            or feature_group_summary["weak_groups"]
        )
        top_weak_features = self._top_weak_features(
            scored_features=scored_features,
            high_missing_features=high_missing_features,
            constant_features=constant_features,
            low_variance_features=low_variance_features,
        )

        recommendations = self._recommendations(
            weak_feature_warnings=weak_feature_warnings,
            top_candidate_features=scored_features[:3],
        )
        recommendations.extend(feature_group_summary["recommendations"])
        return {
            "diagnostic_name": FEATURE_QUALITY_DIAGNOSTIC_NAME,
            "diagnostic_version": FEATURE_QUALITY_DIAGNOSTIC_VERSION,
            "feature_count": len(feature_names),
            "row_count": row_count,
            "label_distribution": label_distribution,
            "missing_value_summary": missing_value_summary,
            "constant_feature_count": len(constant_features),
            "high_missing_feature_count": len(high_missing_features),
            "low_variance_feature_count": len(low_variance_features),
            "weak_signal_detected": weak_signal_detected,
            "feature_signal_score": round(feature_signal_score, 6),
            "feature_group_summary": feature_group_summary,
            "top_weak_features": top_weak_features,
            "top_candidate_features": scored_features[:10],
            "weak_feature_warnings": weak_feature_warnings,
            "recommendations": list(dict.fromkeys(recommendations)),
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
    def _label_distribution(rows: list[dict[str, Any]], label_key: str) -> dict[str, float]:
        counts = Counter(str(row.get(label_key, "UNKNOWN")) for row in rows)
        total = sum(counts.values())
        if total == 0:
            return {}
        return {
            label: count / total
            for label, count in sorted(counts.items())
        }

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
    def _feature_signal_score(
        *,
        scored_features: list[dict[str, Any]],
        constant_feature_count: int,
        high_missing_feature_count: int,
        low_variance_feature_count: int,
    ) -> float:
        top_scores = [
            float(item["separation_score"])
            for item in scored_features[:5]
            if item["separation_score"] is not None
        ]
        base_score = (sum(top_scores) / len(top_scores)) if top_scores else 0.0
        penalty = (
            constant_feature_count * 0.01
            + high_missing_feature_count * 0.01
            + low_variance_feature_count * 0.01
        )
        return max(base_score - penalty, 0.0)

    @staticmethod
    def _top_weak_features(
        *,
        scored_features: list[dict[str, Any]],
        high_missing_features: list[str],
        constant_features: list[str],
        low_variance_features: list[str],
    ) -> list[dict[str, Any]]:
        weak_names = set(high_missing_features) | set(constant_features) | set(low_variance_features)
        ranked = sorted(
            scored_features,
            key=lambda item: (
                item["feature_name"] not in weak_names,
                float(item["separation_score"] or 0.0),
                -item["missing_count"],
            ),
        )
        payload: list[dict[str, Any]] = []
        for item in ranked[:10]:
            reasons: list[str] = []
            feature_name = str(item["feature_name"])
            if feature_name in high_missing_features:
                reasons.append("high_missing")
            if feature_name in constant_features:
                reasons.append("constant")
            if feature_name in low_variance_features:
                reasons.append("low_variance")
            if float(item["separation_score"] or 0.0) <= 0.05:
                reasons.append("low_separation")
            payload.append({**item, "weak_reasons": reasons})
        return payload

    @staticmethod
    def _recommendations(
        *,
        weak_feature_warnings: list[str],
        top_candidate_features: list[dict[str, Any]],
    ) -> list[str]:
        recommendations = []
        if "constant_features_detected" in weak_feature_warnings:
            recommendations.append("Remove or replace constant features before the next experiment.")
        if "high_missing_features_detected" in weak_feature_warnings:
            recommendations.append("Reduce feature missingness or impute consistently before training.")
        if "low_variance_features_detected" in weak_feature_warnings:
            recommendations.append("Down-rank low-variance features because they add little directional separation.")
        if "feature_signal_score_too_low" in weak_feature_warnings:
            recommendations.append("Expand or replace weak features because the current matrix shows low class separation.")
        if top_candidate_features:
            recommendations.append(
                "Review top candidate features first: "
                + ", ".join(item["feature_name"] for item in top_candidate_features)
            )
        if not recommendations:
            recommendations.append("Feature matrix looks usable; validate it with a broader label grid run.")
        return recommendations
