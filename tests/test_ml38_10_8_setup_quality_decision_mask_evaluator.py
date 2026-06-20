from __future__ import annotations

import torch

from app.training.evaluator import Evaluator


class SetupQualityDecisionMaskModel(torch.nn.Module):
    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        return {
            "direction_logits": torch.tensor(
                [[2.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
                dtype=torch.float32,
            ),
            "opportunity_logit": torch.tensor([1.2, 1.1, 1.3], dtype=torch.float32),
            "tp_sl_logits": torch.zeros(3, dtype=torch.float32),
            "expected_move_atr": torch.zeros(3, dtype=torch.float32),
            "risk_score": torch.zeros(3, dtype=torch.float32),
        }


def _dataset() -> dict[str, torch.Tensor]:
    return {
        "features": torch.tensor([[1.0], [2.0], [3.0]], dtype=torch.float32),
        "direction_target": torch.tensor([2, 0, 1], dtype=torch.long),
        "opportunity_target": torch.tensor([0.0, 1.0, 1.0], dtype=torch.float32),
        "direction_trade_target": torch.tensor([0, 0, 1], dtype=torch.long),
        "direction_trade_mask": torch.tensor([0.0, 1.0, 1.0], dtype=torch.float32),
        "tp_sl_target": torch.tensor([0.0, 1.0, 1.0], dtype=torch.float32),
        "tp_sl_mask": torch.tensor([0.0, 1.0, 1.0], dtype=torch.float32),
        "move_target": torch.tensor([0.0, 1.0, 1.0], dtype=torch.float32),
        "risk_target": torch.tensor([0.0, 0.2, 0.2], dtype=torch.float32),
        "setup_quality_score": torch.tensor([0.0, 0.85, 0.30], dtype=torch.float32),
    }


def test_evaluator_applies_setup_quality_decision_mask_and_handles_missing_scores() -> None:
    evaluator = Evaluator()
    dataset = _dataset()

    unmasked_metrics = evaluator.evaluate(
        SetupQualityDecisionMaskModel(),
        dataset,
        opportunity_probability_threshold=0.65,
        training_objective="trade_two_stage",
    )
    masked_metrics = evaluator.evaluate(
        SetupQualityDecisionMaskModel(),
        dataset,
        opportunity_probability_threshold=0.65,
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    assert unmasked_metrics["predicted_trade_rate"] == 1.0
    assert masked_metrics["predicted_trade_rate"] == (1.0 / 3.0)
    assert masked_metrics["setup_quality_decision_mask_enabled"] is True
    assert masked_metrics["setup_quality_decision_mask_min_threshold"] == 0.60
    assert masked_metrics["raw_predicted_trade_rate"] == 1.0

    dataset_without_quality = dict(dataset)
    dataset_without_quality.pop("setup_quality_score")
    missing_score_metrics = evaluator.evaluate(
        SetupQualityDecisionMaskModel(),
        dataset_without_quality,
        opportunity_probability_threshold=0.65,
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    assert missing_score_metrics["predicted_trade_rate"] == 0.0
    assert missing_score_metrics["setup_quality_forced_no_trade_count"] == 3
