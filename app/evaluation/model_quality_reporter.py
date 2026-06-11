from __future__ import annotations

import json
from typing import Any

from app.evaluation.model_quality_validator import ModelQualityValidationResult


class ModelQualityReporter:
    """Serialize model quality validation results."""

    def build_full_quality_report(
        self,
        result: ModelQualityValidationResult,
    ) -> dict[str, Any]:
        return result.to_dict()

    def build_compact_quality_summary(
        self,
        result: ModelQualityValidationResult,
    ) -> dict[str, Any]:
        payload = result.to_dict()
        return {
            "validator_name": payload["validator_name"],
            "validator_version": payload["validator_version"],
            "quality_status": payload["quality_status"],
            "sample_mode": payload["sample_mode"],
            "real_training_executed": payload["real_training_executed"],
            "model_version": payload["model_version"],
            "baseline_accuracy": payload["baseline_accuracy"],
            "model_accuracy": payload["model_accuracy"],
            "accuracy_edge": payload["accuracy_edge"],
            "collapse_detected": payload["collapse_detected"],
            "approved_for_traders_core_integration": payload[
                "approved_for_traders_core_integration"
            ],
            "approved_for_live_trading": payload["approved_for_live_trading"],
            "approved_for_auto_activation": payload[
                "approved_for_auto_activation"
            ],
            "reason_count": len(payload["reasons"]),
            "warning_count": len(payload["warnings"]),
        }

    def full_report_to_json(
        self,
        result: ModelQualityValidationResult,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.build_full_quality_report(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_json(
        self,
        result: ModelQualityValidationResult,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.build_compact_quality_summary(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )
