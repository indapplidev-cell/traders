from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LabelGridCandidate:
    label_version: str
    horizon_candles: int
    direction_atr_threshold: float
    take_profit_atr: float
    stop_loss_atr: float
    dataset_rows: int
    train_rows: int
    validation_rows: int
    test_rows: int
    label_counts_train: dict[str, int]
    label_counts_validation: dict[str, int]
    label_counts_test: dict[str, int]
    best_baseline_name: str
    best_baseline_accuracy: float
    flat_ratio_test: float
    up_ratio_test: float
    down_ratio_test: float
    candidate_score: float
    reject_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_version": self.label_version,
            "horizon_candles": self.horizon_candles,
            "direction_atr_threshold": self.direction_atr_threshold,
            "take_profit_atr": self.take_profit_atr,
            "stop_loss_atr": self.stop_loss_atr,
            "dataset_rows": self.dataset_rows,
            "train_rows": self.train_rows,
            "validation_rows": self.validation_rows,
            "test_rows": self.test_rows,
            "label_counts_train": self.label_counts_train,
            "label_counts_validation": self.label_counts_validation,
            "label_counts_test": self.label_counts_test,
            "best_baseline_name": self.best_baseline_name,
            "best_baseline_accuracy": self.best_baseline_accuracy,
            "flat_ratio_test": self.flat_ratio_test,
            "up_ratio_test": self.up_ratio_test,
            "down_ratio_test": self.down_ratio_test,
            "candidate_score": self.candidate_score,
            "reject_reason": self.reject_reason,
        }
