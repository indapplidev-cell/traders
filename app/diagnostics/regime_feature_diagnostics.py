from __future__ import annotations

from collections import Counter
from typing import Any

from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics


REGIME_FEATURE_DIAGNOSTIC_NAME = "regime_feature_diagnostics"
REGIME_FEATURE_DIAGNOSTIC_VERSION = "ml32"


class RegimeFeatureDiagnostics:
    """Analyze feature quality and label balance across detected market regimes."""

    REGIME_NAME_MAP = {
        "regime_trend_up": "trend_up",
        "regime_trend_down": "trend_down",
        "regime_range": "range",
        "regime_high_volatility": "high_volatility",
        "regime_low_volatility": "low_volatility",
        "regime_unknown": "unknown",
    }

    def __init__(
        self,
        *,
        feature_quality_diagnostics: FeatureQualityDiagnostics | None = None,
    ) -> None:
        self._feature_quality_diagnostics = feature_quality_diagnostics or FeatureQualityDiagnostics()

    def analyze(
        self,
        rows: list[dict[str, Any]],
        *,
        label_key: str = "direction_label",
        features_key: str = "features_json",
    ) -> dict[str, Any]:
        feature_names = self._feature_names(rows, features_key)
        regime_feature_names = [
            name for name in feature_names if name.startswith("regime_")
        ]
        if not regime_feature_names:
            return {
                "diagnostic_name": REGIME_FEATURE_DIAGNOSTIC_NAME,
                "diagnostic_version": REGIME_FEATURE_DIAGNOSTIC_VERSION,
                "row_count": len(rows),
                "feature_count": len(feature_names),
                "regime_data_available": False,
                "regime_counts": {},
                "label_distribution_by_regime": {},
                "feature_quality_by_regime": {},
                "weak_regimes": [],
                "strong_regimes": [],
                "warnings": ["regime_data_unavailable"],
                "recommendations": [
                    "Build or attach regime labels before regime-specific training.",
                ],
            }

        regime_rows: dict[str, list[dict[str, Any]]] = {}
        for regime_feature_name in regime_feature_names:
            regime_name = self._normalize_regime_name(regime_feature_name)
            regime_rows[regime_name] = [
                row
                for row in rows
                if float(dict(row.get(features_key, {})).get(regime_feature_name, 0.0) or 0.0) == 1.0
            ]

        unknown_rows = [
            row
            for row in rows
            if not any(
                float(dict(row.get(features_key, {})).get(name, 0.0) or 0.0) == 1.0
                for name in regime_feature_names
            )
        ]
        regime_rows["unknown"] = unknown_rows

        regime_counts = {name: len(items) for name, items in regime_rows.items()}
        label_distribution_by_regime = {
            name: self._label_distribution(items, label_key=label_key)
            for name, items in regime_rows.items()
        }
        feature_quality_by_regime: dict[str, Any] = {}
        weak_regimes: list[str] = []
        strong_regimes: list[str] = []
        warnings: list[str] = []

        for regime_name, items in regime_rows.items():
            quality = self._feature_quality_diagnostics.analyze(
                items,
                label_key=label_key,
                features_key=features_key,
            )
            feature_quality_by_regime[regime_name] = {
                "row_count": len(items),
                "feature_signal_score": quality["feature_signal_score"],
                "weak_signal_detected": quality["weak_signal_detected"],
                "top_candidate_features": [
                    item["feature_name"] for item in quality["top_candidate_features"][:3]
                ],
                "top_weak_features": [
                    item["feature_name"] for item in quality["top_weak_features"][:3]
                ],
            }
            if len(items) < 20:
                warnings.append(f"regime_rows_too_small:{regime_name}")
            if quality["weak_signal_detected"] or len(items) < 20:
                weak_regimes.append(regime_name)
            elif quality["feature_signal_score"] >= 0.20:
                strong_regimes.append(regime_name)

        return {
            "diagnostic_name": REGIME_FEATURE_DIAGNOSTIC_NAME,
            "diagnostic_version": REGIME_FEATURE_DIAGNOSTIC_VERSION,
            "row_count": len(rows),
            "feature_count": len(feature_names),
            "regime_data_available": True,
            "regime_counts": regime_counts,
            "label_distribution_by_regime": label_distribution_by_regime,
            "feature_quality_by_regime": feature_quality_by_regime,
            "weak_regimes": sorted(dict.fromkeys(weak_regimes)),
            "strong_regimes": sorted(dict.fromkeys(strong_regimes)),
            "warnings": sorted(dict.fromkeys(warnings)),
            "recommendations": self._recommendations(
                weak_regimes=weak_regimes,
                strong_regimes=strong_regimes,
            ),
        }

    @staticmethod
    def _feature_names(rows: list[dict[str, Any]], features_key: str) -> list[str]:
        names: set[str] = set()
        for row in rows:
            for feature_name in dict(row.get(features_key, {})).keys():
                names.add(str(feature_name))
        return sorted(names)

    @staticmethod
    def _label_distribution(rows: list[dict[str, Any]], *, label_key: str) -> dict[str, float]:
        counts = Counter(str(row.get(label_key, "UNKNOWN")) for row in rows)
        total = sum(counts.values())
        if total <= 0:
            return {}
        return {
            label: count / total
            for label, count in sorted(counts.items())
        }

    def _normalize_regime_name(self, feature_name: str) -> str:
        if feature_name in self.REGIME_NAME_MAP:
            return self.REGIME_NAME_MAP[feature_name]
        return feature_name.removeprefix("regime_") or feature_name

    @staticmethod
    def _recommendations(*, weak_regimes: list[str], strong_regimes: list[str]) -> list[str]:
        recommendations: list[str] = []
        if weak_regimes:
            recommendations.append(
                "Focus regime-specific training on weak regimes first: "
                + ", ".join(sorted(dict.fromkeys(weak_regimes)))
            )
        if strong_regimes:
            recommendations.append(
                "Use the strongest regimes as the first candidates for regime-aware experiments: "
                + ", ".join(sorted(dict.fromkeys(strong_regimes)))
            )
        if not recommendations:
            recommendations.append("Regime coverage is present but inconclusive; review sample size before training.")
        return recommendations
