from __future__ import annotations

from typing import Any


ANTI_COLLAPSE_TRAINING_PLAN_NAME = "anti_collapse_training_plan"
ANTI_COLLAPSE_TRAINING_PLAN_VERSION = "ml30"


class AntiCollapseTrainingPlan:
    """Describe safer training controls for reducing directional collapse."""

    def build_plan(self) -> dict[str, Any]:
        return {
            "plan_name": ANTI_COLLAPSE_TRAINING_PLAN_NAME,
            "plan_version": ANTI_COLLAPSE_TRAINING_PLAN_VERSION,
            "class_balance_strategy": "enable_class_weights_and_review_balanced_sampling",
            "sample_weight_strategy": "increase_weight_for_underrepresented_DOWN_and_FLAT_cases",
            "loss_weight_strategy": "preserve_multitask_loss_with_direction_class_weights",
            "confidence_margin_strategy": "raise_min_prediction_margin_before_signal_acceptance",
            "prediction_distribution_gate": {
                "max_predicted_class_share": 0.70,
                "min_down_prediction_share": 0.15,
                "actual_down_share_trigger": 0.30,
            },
            "recommended_thresholds": {
                "stronger_flat_separation": True,
                "min_prediction_margin": 0.05,
                "max_prob_gate_floor": 0.45,
            },
            "expected_effect": [
                "Reduce UP-dominant prediction collapse.",
                "Increase penalty on direction imbalance before candidate acceptance.",
                "Preserve research-only safety boundaries while making training controls explicit.",
            ],
            "risks": [
                "Class balancing can reduce raw accuracy if labels remain noisy.",
                "Stricter confidence gates can lower signal count.",
                "Balanced sampling requires validation against walk-forward stability.",
            ],
            "class_weights_supported": True,
            "trainer_integration": "optional_existing_disable_class_weights_flag_false_by_default",
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }
