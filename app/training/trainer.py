from __future__ import annotations

from typing import Any

import torch

from app.training.evaluator import Evaluator
from app.training.loss import MultiTaskLoss


class Trainer:
    def __init__(
        self,
        epochs: int = 20,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        loss_fn: MultiTaskLoss | None = None,
        evaluator: Evaluator | None = None,
        training_objective: str = "direction_global",
    ) -> None:
        self._epochs = epochs
        self._learning_rate = learning_rate
        self._weight_decay = weight_decay
        self._loss_fn = loss_fn or MultiTaskLoss()
        self._evaluator = evaluator or Evaluator()
        self._training_objective = training_objective

    def train(
        self,
        model: torch.nn.Module,
        train_dataset: dict[str, torch.Tensor],
        validation_dataset: dict[str, torch.Tensor],
    ) -> dict[str, Any]:
        optimizer = torch.optim.Adam(model.parameters(), lr=self._learning_rate, weight_decay=self._weight_decay)
        history: list[dict[str, float]] = []

        for epoch in range(self._epochs):
            model.train()
            optimizer.zero_grad()
            outputs = model(train_dataset["features"])
            total_loss, losses = self._loss_fn.compute(outputs, train_dataset)
            total_loss.backward()
            optimizer.step()

            epoch_record = {"epoch": float(epoch + 1), **losses}
            if validation_dataset["features"].shape[0] > 0:
                validation_metrics = self._evaluator.evaluate(
                    model,
                    validation_dataset,
                    training_objective=self._training_objective,
                )
                epoch_record["validation_accuracy"] = float(validation_metrics["accuracy"])
                epoch_record["validation_brier_score"] = float(validation_metrics["brier_score"])
            history.append(epoch_record)

        return {
            "epochs": self._epochs,
            "history": history,
            "final_train_loss": history[-1]["total_loss"] if history else None,
        }
