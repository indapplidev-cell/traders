from __future__ import annotations

from typing import Any


FEATURE_ENGINEERING_PLAN_NAME = "feature_engineering_plan"
FEATURE_ENGINEERING_PLAN_VERSION = "ml32"


class FeatureEngineeringPlan:
    """Describe the currently wired ML34 feature-engineering surface."""

    def build_plan(self) -> dict[str, Any]:
        return {
            "plan_name": FEATURE_ENGINEERING_PLAN_NAME,
            "plan_version": "ml34",
            "builder_changed": True,
            "current_coverage": [
                "return_1",
                "return_3",
                "return_6",
                "range_pct",
                "body_pct",
                "upper_wick_pct",
                "lower_wick_pct",
                "volume_change_pct",
                "atr_normalized_move",
                "trend_slope_short",
                "trend_slope_medium",
                "regime_trend_up",
                "regime_trend_down",
                "regime_range",
                "regime_high_volatility",
                "regime_low_volatility",
                "regime_unknown",
            ],
            "planned_additive_features": [],
            "active_feature_versions": ["fv1", "fv2", "fv2_regime"],
            "reason": "ML34 wires additive features and regime flags into a real selectable feature version while keeping fv1 backward compatible.",
            "recommendations": [
                "Prefer fv2 for feature/regime-aware experiments.",
                "Keep fv1 available for backward-compatible baselines and comparisons.",
            ],
        }
