from __future__ import annotations

from typing import Any

from app.diagnostics.feature_group_quality import FeatureGroupQualityScorer
from app.diagnostics.feature_leakage_guard import FeatureLeakageGuard
from app.diagnostics.feature_quality_diagnostics import FeatureQualityDiagnostics
from app.diagnostics.regime_feature_diagnostics import RegimeFeatureDiagnostics
from app.features.feature_models import (
    CANDLE_MORPHOLOGY_FEATURE_NAMES,
    CANDLE_PATTERN_FEATURE_NAMES,
    FV4_BOOK_SETUP_CONTEXT_FEATURE_NAMES,
    FV3_CANDLE_TA_CONTEXT_FEATURE_NAMES,
    HTF_CONTEXT_FEATURE_NAMES,
    NISON_CONTEXT_FEATURE_NAMES,
    ALTUNINA_CONTEXT_FEATURE_NAMES,
    PATH_CONTEXT_FEATURE_NAMES,
    SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES,
    TECHNICAL_CONTEXT_FEATURE_NAMES,
)


class RealFeatureDiagnosticsService:
    DIAGNOSTIC_NAME = "real_feature_diagnostics_service"
    DIAGNOSTIC_VERSION = "ml36"
    FV3_FEATURE_VERSION = "fv3_candle_ta_context"
    FV4_FEATURE_VERSION = "fv4_book_setup_context"
    FV3_REQUIRED_FEATURES = {
        "doji_score",
        "hammer_score",
        "trend_slope_long",
        "distance_to_support",
        "bollinger_position",
        "stochastic_k",
        "volume_zscore",
    }
    FV4_REQUIRED_FEATURES = {
        "nison_reversal_context_score",
        "alt_trend_continuation_long_score",
        "path_8_high_low_expansion_atr",
        "schwager_false_breakout_risk_score",
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
            candle_ta_context_missing_reason = None
            book_setup_context_missing_reason = None
            if feature_version == self.FV3_FEATURE_VERSION:
                candle_ta_context_missing_reason = reason or "fv3_candle_ta_context_rows_unavailable"
            if feature_version == self.FV4_FEATURE_VERSION:
                book_setup_context_missing_reason = reason or "fv4_book_setup_context_rows_unavailable"
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
                "candle_morphology_feature_count": 0,
                "candle_pattern_feature_count": 0,
                "technical_context_feature_count": 0,
                "candle_ta_context_feature_count": 0,
                "fv4_feature_count": 0,
                "book_setup_context_feature_count": 0,
                "nison_feature_count": 0,
                "altunina_feature_count": 0,
                "path_context_feature_count": 0,
                "htf_context_feature_count": 0,
                "missing_context_feature_count": len(HTF_CONTEXT_FEATURE_NAMES)
                if feature_version == self.FV4_FEATURE_VERSION
                else 0,
                "regime_feature_count": 0,
                "candle_ta_context_features_attached": False,
                "book_setup_context_features_attached": False,
                "candle_ta_context_missing_reason": candle_ta_context_missing_reason,
                "book_setup_context_missing_reason": book_setup_context_missing_reason,
                "higher_timeframe_context_available": False,
                "higher_timeframe_context_reason": (
                    "not_integrated_yet" if feature_version == self.FV4_FEATURE_VERSION else None
                ),
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
        feature_names = set(self._feature_names(normalized_rows))
        feature_count = len(feature_names)
        candle_ta_context_features_attached = self._has_fv3_feature_set(normalized_rows)
        book_setup_context_features_attached = self._has_fv4_feature_set(normalized_rows)
        candle_ta_context_missing_reason = None
        if feature_version == self.FV3_FEATURE_VERSION and not candle_ta_context_features_attached:
            candle_ta_context_missing_reason = "fv3_required_features_missing_from_rows"
        book_setup_context_missing_reason = None
        if feature_version == self.FV4_FEATURE_VERSION and not book_setup_context_features_attached:
            book_setup_context_missing_reason = "fv4_required_features_missing_from_rows"
        higher_timeframe_context_available = False
        higher_timeframe_context_reason = (
            "not_integrated_yet" if feature_version == self.FV4_FEATURE_VERSION else None
        )
        nison_feature_count = self._count_present_features(feature_names, NISON_CONTEXT_FEATURE_NAMES)
        altunina_feature_count = self._count_present_features(feature_names, ALTUNINA_CONTEXT_FEATURE_NAMES)
        path_context_feature_count = self._count_present_features(feature_names, PATH_CONTEXT_FEATURE_NAMES)
        schwager_trap_feature_count = self._count_present_features(
            feature_names,
            SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES,
        )
        htf_context_feature_count = 0 if not higher_timeframe_context_available else self._count_present_features(
            feature_names,
            HTF_CONTEXT_FEATURE_NAMES,
        )
        missing_context_feature_count = (
            len(HTF_CONTEXT_FEATURE_NAMES) - htf_context_feature_count
            if feature_version == self.FV4_FEATURE_VERSION
            else 0
        )
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
            "candle_morphology_feature_count": self._count_present_features(
                feature_names,
                CANDLE_MORPHOLOGY_FEATURE_NAMES,
            ),
            "candle_pattern_feature_count": self._count_present_features(
                feature_names,
                CANDLE_PATTERN_FEATURE_NAMES,
            ),
            "technical_context_feature_count": self._count_present_features(
                feature_names,
                TECHNICAL_CONTEXT_FEATURE_NAMES,
            ),
            "candle_ta_context_feature_count": self._count_present_features(
                feature_names,
                FV3_CANDLE_TA_CONTEXT_FEATURE_NAMES,
            ),
            "fv4_feature_count": self._count_present_features(
                feature_names,
                FV4_BOOK_SETUP_CONTEXT_FEATURE_NAMES,
            ),
            "book_setup_context_feature_count": (
                nison_feature_count
                + altunina_feature_count
                + path_context_feature_count
                + schwager_trap_feature_count
                + htf_context_feature_count
            ),
            "nison_feature_count": nison_feature_count,
            "altunina_feature_count": altunina_feature_count,
            "path_context_feature_count": path_context_feature_count,
            "schwager_trap_feature_count": schwager_trap_feature_count,
            "htf_context_feature_count": htf_context_feature_count,
            "missing_context_feature_count": missing_context_feature_count,
            "regime_feature_count": sum(int(name.startswith("regime_")) for name in feature_names),
            "candle_ta_context_features_attached": candle_ta_context_features_attached,
            "book_setup_context_features_attached": book_setup_context_features_attached,
            "candle_ta_context_missing_reason": candle_ta_context_missing_reason,
            "book_setup_context_missing_reason": book_setup_context_missing_reason,
            "higher_timeframe_context_available": higher_timeframe_context_available,
            "higher_timeframe_context_reason": higher_timeframe_context_reason,
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

    @staticmethod
    def _count_present_features(feature_names: set[str], expected_names: list[str]) -> int:
        return sum(int(name in feature_names) for name in expected_names)

    @classmethod
    def _has_fv3_feature_set(cls, rows: list[dict[str, Any]]) -> bool:
        feature_names = set(cls._feature_names(rows))
        return cls.FV3_REQUIRED_FEATURES.issubset(feature_names)

    @classmethod
    def _has_fv4_feature_set(cls, rows: list[dict[str, Any]]) -> bool:
        feature_names = set(cls._feature_names(rows))
        return cls.FV4_REQUIRED_FEATURES.issubset(feature_names)
