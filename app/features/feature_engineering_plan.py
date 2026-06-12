from __future__ import annotations

from typing import Any


FEATURE_ENGINEERING_PLAN_NAME = "feature_engineering_plan"
FEATURE_ENGINEERING_PLAN_VERSION = "ml32"


class FeatureEngineeringPlan:
    """Describe safe additive feature ideas without mutating the current schema."""

    def build_plan(self) -> dict[str, Any]:
        return {
            "plan_name": FEATURE_ENGINEERING_PLAN_NAME,
            "plan_version": FEATURE_ENGINEERING_PLAN_VERSION,
            "builder_changed": False,
            "current_coverage": [
                "return_1",
                "return_3",
                "range_percent",
                "body_to_range_ratio",
                "ema_9_slope_3",
                "close_slope_10",
                "regime_trend_up",
            ],
            "planned_additive_features": [
                "return_6",
                "body_pct",
                "upper_wick_pct",
                "lower_wick_pct",
                "volume_change_pct",
                "atr_normalized_move",
                "trend_slope_short",
                "trend_slope_medium",
            ],
            "reason": "Current feature schema already covers part of the requested signal family; defer additive schema changes to ML33 to avoid unnecessary dataset churn.",
            "recommendations": [
                "Keep the current feature builder stable in ML32.",
                "Use ML32 diagnostics to decide which additive features deserve real implementation in ML33.",
            ],
        }
