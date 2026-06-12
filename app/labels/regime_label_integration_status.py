from __future__ import annotations

from typing import Any


class RegimeLabelIntegrationStatus:
    STATUS_NAME = "regime_label_integration_status"
    STATUS_VERSION = "ml34"

    def build_status(
        self,
        *,
        regime_specific_labeling_available: bool,
        regime_features_attached: bool,
        regime_feature_count: int,
        training_pipeline_supports_regime_labels: bool = False,
    ) -> dict[str, Any]:
        missing_requirements: list[str] = []
        if not regime_specific_labeling_available:
            missing_requirements.append("regime_specific_label_configs_unavailable")
        if not regime_features_attached or regime_feature_count <= 0:
            missing_requirements.append("regime_features_not_attached")
        if not training_pipeline_supports_regime_labels:
            missing_requirements.append("regime_specific_label_builder_not_wired_into_training_pipeline")

        regime_specific_training_applied = (
            regime_specific_labeling_available
            and regime_features_attached
            and regime_feature_count > 0
            and training_pipeline_supports_regime_labels
        )
        return {
            "status_name": self.STATUS_NAME,
            "status_version": self.STATUS_VERSION,
            "regime_specific_labeling_available": regime_specific_labeling_available,
            "regime_specific_training_applied": regime_specific_training_applied,
            "regime_features_attached": regime_features_attached,
            "missing_requirements": missing_requirements,
            "next_steps": self._next_steps(missing_requirements),
        }

    @staticmethod
    def _next_steps(missing_requirements: list[str]) -> list[str]:
        if not missing_requirements:
            return ["Regime-specific training is wired and ready for controlled research runs."]

        steps: list[str] = []
        if "regime_specific_label_configs_unavailable" in missing_requirements:
            steps.append("Define or load regime-specific label configurations before training.")
        if "regime_features_not_attached" in missing_requirements:
            steps.append("Attach regime features to the dataset before enabling regime-aware training.")
        if "regime_specific_label_builder_not_wired_into_training_pipeline" in missing_requirements:
            steps.append("Wire regime-specific label selection into the real training pipeline before claiming applied training.")
        return steps
