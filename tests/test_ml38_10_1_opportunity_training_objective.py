from datetime import datetime, timezone

import torch

from app.dataset.dataset_models import DatasetRow
from app.training.loss import MultiTaskLoss
from app.training.training_service import TrainingService


def test_opportunity_first_tensor_contract_uses_setup_targets() -> None:
    rows = [
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
            feature_version="fv4_book_setup_context",
            label_version="lv13_h12_opportunity_ft",
            horizon_candles=12,
            features_json={"x": 1.0},
            direction_label="UP",
            tp_before_sl=True,
            future_return=0.01,
            future_move_atr=0.8,
            max_favorable_move_atr=1.1,
            max_adverse_move_atr=0.4,
            opportunity_label=1,
            setup_type="nison_context",
            setup_quality_score=0.8,
            setup_expected_move_atr=1.3,
            setup_invalidation_distance_atr=0.25,
            label_ambiguity_score=0.2,
        ),
        DatasetRow(
            symbol="BTCUSDT",
            interval="15m",
            candle_open_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
            feature_version="fv4_book_setup_context",
            label_version="lv13_h12_opportunity_ft",
            horizon_candles=12,
            features_json={"x": 2.0},
            direction_label="FLAT",
            tp_before_sl=None,
            future_return=0.0,
            future_move_atr=0.05,
            max_favorable_move_atr=0.1,
            max_adverse_move_atr=0.08,
            opportunity_label=0,
            setup_type="no_setup",
            setup_quality_score=0.1,
            setup_expected_move_atr=0.05,
            setup_invalidation_distance_atr=0.08,
            label_ambiguity_score=0.9,
        ),
    ]

    tensors = TrainingService.rows_to_tensors(
        rows=rows,
        feature_columns=["x"],
        scaler={"mean": [0.0], "std": [1.0]},
        training_objective="opportunity_first",
    )

    assert tensors["opportunity_target"].tolist() == [1.0, 0.0]
    assert abs(float(tensors["move_target"][0].item()) - 1.3) < 1e-6
    assert abs(float(tensors["risk_target"][0].item()) - 0.25) < 1e-6


def test_opportunity_first_loss_reports_opportunity_component() -> None:
    loss_fn = MultiTaskLoss(training_objective="opportunity_first")
    batch = {
        "direction_target": torch.tensor([0, 2]),
        "direction_sample_weight": torch.tensor([1.0, 1.0]),
        "tp_sl_target": torch.tensor([1.0, 0.0]),
        "tp_sl_mask": torch.tensor([1.0, 0.0]),
        "move_target": torch.tensor([1.2, 0.0]),
        "risk_target": torch.tensor([0.3, 0.0]),
        "opportunity_target": torch.tensor([1.0, 0.0]),
    }
    outputs = {
        "direction_logits": torch.tensor([[2.0, 0.5, -1.0], [0.1, 0.1, 0.1]]),
        "opportunity_logit": torch.tensor([1.5, -1.2]),
        "tp_sl_logits": torch.tensor([0.8, 0.0]),
        "expected_move_atr": torch.tensor([1.0, 0.1]),
        "risk_score": torch.tensor([0.4, 0.1]),
    }

    total_loss, metrics = loss_fn.compute(outputs, batch)

    assert float(total_loss.item()) >= 0.0
    assert metrics["training_objective"] == "opportunity_first"
    assert "opportunity_loss" in metrics
    assert metrics["direction_loss"] >= 0.0
