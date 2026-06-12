from __future__ import annotations

from typing import Any

from app.features.feature_engineering_plan import FeatureEngineeringPlan
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.labels.regime_label_config import RegimeLabelConfigPlanner


REGIME_EXPERIMENT_PLANNER_NAME = "regime_experiment_planner"
REGIME_EXPERIMENT_PLANNER_VERSION = "ml32"


class RegimeExperimentPlanner:
    """Build a regime-aware experiment plan for ML33 preparation."""

    def __init__(
        self,
        *,
        grid_planner: LabelQualityGridPlanner | None = None,
        regime_label_planner: RegimeLabelConfigPlanner | None = None,
        feature_engineering_plan: FeatureEngineeringPlan | None = None,
    ) -> None:
        self._grid_planner = grid_planner or LabelQualityGridPlanner()
        self._regime_label_planner = regime_label_planner or RegimeLabelConfigPlanner()
        self._feature_engineering_plan = feature_engineering_plan or FeatureEngineeringPlan()

    def build_plan(
        self,
        *,
        symbol: str,
        interval: str,
        start_date: str,
        regime_data_available: bool,
        base_label_config_id: str = "lv2_h12_thr05_tp15_sl10",
    ) -> dict[str, Any]:
        base_configs = self._grid_planner.build_grid()["configs"]
        regime_configs = self._regime_label_planner.build_configs(
            base_label_config_id=base_label_config_id
        )["configs"]
        required_data = [
            "fv2_regime feature rows",
            "regime assignments in dataset rows",
            "label coverage by regime",
            "gap-aware filtered training windows",
        ]
        missing_data: list[str] = []
        if not regime_data_available:
            missing_data.append("regime assignments in dataset/features")

        ready_for_real_regime_training = not missing_data
        payload = {
            "planner_name": REGIME_EXPERIMENT_PLANNER_NAME,
            "planner_version": REGIME_EXPERIMENT_PLANNER_VERSION,
            "symbol": symbol,
            "interval": interval,
            "start_date": start_date,
            "base_configs": base_configs,
            "regime_configs": regime_configs,
            "required_data": required_data,
            "missing_data": missing_data,
            "experiment_steps": [
                "Validate regime-aware feature diagnostics on fv2_regime rows.",
                "Review weak feature groups and leakage warnings.",
                "Attach or verify regime membership in dataset rows.",
                "Preview regime-specific label configs before real retraining.",
                "Run ML33 research experiments with the strongest regime candidates first.",
            ],
            "risks": [
                "Regime rows can stay sparse even when regime flags exist.",
                "Feature quality may differ sharply between trend and range segments.",
                "Label fragmentation can increase instability if regime mapping is noisy.",
            ],
            "recommendations": self._recommendations(regime_data_available=regime_data_available),
            "ready_for_real_regime_training": ready_for_real_regime_training,
            "feature_engineering_plan": self._feature_engineering_plan.build_plan(),
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
        if not ready_for_real_regime_training:
            payload["reason"] = "regime data unavailable in dataset/features"
        return payload

    @staticmethod
    def _recommendations(*, regime_data_available: bool) -> list[str]:
        recommendations = [
            "Keep traders-core disconnected while regime-aware training is still research-only.",
            "Use feature-group and leakage diagnostics before expanding the label search again.",
        ]
        if regime_data_available:
            recommendations.append("Prepare ML33 around the strongest regime-specific label configs first.")
        else:
            recommendations.append("Build or attach regime labels before attempting real regime-specific training.")
        return recommendations
