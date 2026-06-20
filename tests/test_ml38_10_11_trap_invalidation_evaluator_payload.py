import torch

from app.features.feature_models import SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES
from app.training.evaluator import Evaluator


class _DummyTradeTwoStageModel(torch.nn.Module):
    def forward(self, features: torch.Tensor) -> dict[str, torch.Tensor]:
        row_count = features.shape[0]
        direction_logits = torch.tensor(
            [[3.0, 0.5, -2.0]] * row_count,
            dtype=torch.float32,
        )
        opportunity_logit = torch.tensor([2.0] * row_count, dtype=torch.float32)
        return {
            "direction_logits": direction_logits,
            "tp_sl_logits": torch.zeros((row_count,), dtype=torch.float32),
            "expected_move_atr": torch.zeros((row_count,), dtype=torch.float32),
            "risk_score": torch.zeros((row_count,), dtype=torch.float32),
            "opportunity_logit": opportunity_logit,
        }


def test_evaluator_attaches_trap_invalidation_feature_impact_audit() -> None:
    feature_names = tuple(SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES)
    feature_count = len(feature_names)
    raw_feature_values = []
    for index in range(6):
        row = [0.0] * feature_count
        row[0] = 0.10 if index < 3 else 0.90
        raw_feature_values.append(row)

    dataset = {
        "features": torch.tensor(raw_feature_values, dtype=torch.float32),
        "raw_feature_values": torch.tensor(raw_feature_values, dtype=torch.float32),
        "feature_columns": feature_names,
        "direction_target": torch.tensor([0, 0, 0, 2, 2, 2], dtype=torch.long),
        "tp_sl_target": torch.zeros((6,), dtype=torch.float32),
        "tp_sl_mask": torch.zeros((6,), dtype=torch.float32),
        "move_target": torch.zeros((6,), dtype=torch.float32),
        "risk_target": torch.zeros((6,), dtype=torch.float32),
        "opportunity_target": torch.tensor([1, 1, 1, 0, 0, 0], dtype=torch.float32),
        "setup_quality_score": torch.tensor([0.9, 0.9, 0.9, 0.9, 0.9, 0.9], dtype=torch.float32),
    }

    metrics = Evaluator().evaluate(
        _DummyTradeTwoStageModel(),
        dataset,
        opportunity_probability_threshold=0.65,
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    audit = metrics["trap_invalidation_feature_impact_audit"]
    assert audit["diagnostic_name"] == "trap_invalidation_feature_impact_audit"
    assert audit["audit_status"] == "COMPLETED"
    assert audit["trap_feature_count"] == len(SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES)
