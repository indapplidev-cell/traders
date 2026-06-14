from __future__ import annotations

from typing import Any

from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer
from app.diagnostics.feature_leakage_guard import FeatureLeakageGuard
from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics
from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics


class RealFeatureDiagnosticsService:
    DIAGNOSTIC_NAME = "real_feature_diagnostics_service"
    DIAGNOSTIC_VERSION = "ml36"
    FV3_REQUIRED_FEATURES = {
        "doji_score",
        "hammer_score",
        "trend_slope_long",
        "distance_to_support",
        "bollinger_position",
        "stochastic_k",
        "volume_zscore",
    }

    def __init__(
        self,
        *,
        feature_quality_diagnostics: FeatureQualityDiagnostics | None = None,
        feature_group_quality_scorer: FeatureGroupQualityScorer | None = None,
        feature_leakage_guard: FeatureLeakageGuard | None = None,
        regime_feature_diagnostics: RegimeFeatureDiagnostics | None = None,
    ) -> None:
        self._feature_quality_diagnostics = feature_quality_diagnostics or FeatureQualityDiagnostics()
        self._feature_group_quality_scorer = feature_group_quality_scorer or FeatureGroupQualityScorer()
        self._feature_leakage_guard = feature_leakage_guard or FeatureLeakageGuard()
        self._regime_feature_diagnostics = regime_feature_diagnostics or RegimeFeatureDiagnostics()

    def analyze(
        self,
        *,
        symbol: str,
        interval: str,
        feature_version: str,
        label_version: str,
        rows: list[Any] | None,
        source: str,
        sample_mode: bool = False,
        warnings: list[str] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        normalized_rows = self._normalize_rows(rows or [])
        warnings_list = list(warnings or [])
        degraded_mode = not normalized_rows

        if sample_mode:
            warnings_list.append("sample_mode_rows_used")
        if degraded_mode and reason:
            warnings_list.append(reason)

        if degraded_mode:
            recommendations = [
                "Load real dataset rows before relying on feature diagnostics.",
            ]
            if sample_mode:
                recommendations.insert(0, "Sample-mode diagnostics are useful only for wiring checks.")
            return {
                "diagnostic_name": self.DIAGNOSTIC_NAME,
                "diagnostic_version": self.DIAGNOSTIC_VERSION,
                "source": source,
                "symbol": symbol,
                "interval": interval,
                "feature_version": feature_version,
                "label_version": label_version,
                "row_count": 0,
                "feature_count": 0,
                "feature_quality": {
                    "diagnostic_name": "feature_quality_diagnostics",
                    "row_count": 0,
                    "feature_count": 0,
                    "weak_signal_detected": False,
                    "feature_signal_score": 0.0,
                },
                "feature_group_quality": {"group_name": "feature_group_quality", "row_count": 0, "group_count": 0, "weak_groups": []},
                "feature_family_diagnostics": {"group_name": "feature_group_quality", "row_count": 0, "group_count": 0, "weak_groups": []},
                "leakage_guard": {"guard_name": "feature_leakage_guard", "checked_features": 0, "leakage_risk_detected": False},
                "regime_feature_diagnostics": {
                    "diagnostic_name": "regime_feature_diagnostics",
                    "row_count": 0,
                    "feature_count": 0,
                    "regime_data_available": False,
                    "weak_regimes": [],
                    "warnings": ["regime_data_unavailable"],
                },
                "sample_mode": sample_mode,
                "degraded_mode": True,
                "real_feature_diagnostics_used": False,
                "candle_ta_context_features_attached": False,
                "warnings": list(dict.fromkeys(warnings_list or ["dataset_rows_unavailable"])),
                "recommendations": recommendations,
            }

        feature_quality = self._feature_quality_diagnostics.analyze(normalized_rows)
        feature_group_quality = self._feature_group_quality_scorer.analyze(normalized_rows)
        leakage_guard = self._feature_leakage_guard.check_rows(normalized_rows)
        regime_feature_diagnostics = self._regime_feature_diagnostics.analyze(normalized_rows)

        recommendations = (
            list(feature_quality.get("recommendations", []))
            + list(feature_group_quality.get("recommendations", []))
            + list(leakage_guard.get("recommendations", []))
            + list(regime_feature_diagnostics.get("recommendations", []))
        )
        feature_count = len(self._feature_names(normalized_rows))
        return {
            "diagnostic_name": self.DIAGNOSTIC_NAME,
            "diagnostic_version": self.DIAGNOSTIC_VERSION,
            "source": source,
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "label_version": label_version,
            "row_count": len(normalized_rows),
            "feature_count": feature_count,
            "feature_quality": feature_quality,
            "feature_group_quality": feature_group_quality,
            "feature_family_diagnostics": feature_group_quality,
            "leakage_guard": leakage_guard,
            "regime_feature_diagnostics": regime_feature_diagnostics,
            "sample_mode": sample_mode,
            "degraded_mode": False,
            "real_feature_diagnostics_used": not sample_mode,
            "candle_ta_context_features_attached": self._has_fv3_feature_set(normalized_rows),
            "warnings": list(dict.fromkeys(warnings_list)),
            "recommendations": list(dict.fromkeys(recommendations)),
        }

    @staticmethod
    def _normalize_rows(rows: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if isinstance(row, dict):
                features_json = dict(row.get("features_json", {}))
                direction_label = row.get("direction_label")
            else:
                features_json = dict(getattr(row, "features_json", {}))
                direction_label = getattr(row, "direction_label", None)
            normalized.append(
                {
                    "direction_label": direction_label,
                    "features_json": features_json,
                }
            )
        return normalized

    @staticmethod
    def _feature_names(rows: list[dict[str, Any]]) -> list[str]:
        names: set[str] = set()
        for row in rows:
            names.update(str(name) for name in dict(row.get("features_json", {})).keys())
        return sorted(names)

    @classmethod
    def _has_fv3_feature_set(cls, rows: list[dict[str, Any]]) -> bool:
        feature_names = set(cls._feature_names(rows))
        return cls.FV3_REQUIRED_FEATURES.issubset(feature_names)
