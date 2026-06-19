from __future__ import annotations

import torch
from torch import nn


class DirectionHead(nn.Module):
    """Более сильная direction head.

    В ML38.7 temperature scaling показал, что проблема глубже softmax:
    logits сами плохо расходятся. Поэтому direction head получает отдельный
    небольшой MLP-блок, а не простой Linear(64, 3).
    """

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(hidden_dim, 96),
            nn.LayerNorm(96),
            nn.SiLU(),
            nn.Dropout(0.10),
            nn.Linear(96, 48),
            nn.SiLU(),
            nn.Linear(48, 3),
        )

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.layers(hidden)


class AuxiliaryRegressionHead(nn.Module):
    """Маленькая отдельная head для auxiliary targets."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(hidden_dim, 48),
            nn.SiLU(),
            nn.Linear(48, 1),
        )

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        return self.layers(hidden).squeeze(-1)


class CandleMLP(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.SiLU(),
            nn.Dropout(0.20),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.SiLU(),
            nn.Dropout(0.15),
            nn.Linear(128, 96),
            nn.LayerNorm(96),
            nn.SiLU(),
        )
        self.direction_head = DirectionHead(hidden_dim=96)
        self.opportunity_head = AuxiliaryRegressionHead(hidden_dim=96)
        self.tp_sl_head = AuxiliaryRegressionHead(hidden_dim=96)
        self.move_head = AuxiliaryRegressionHead(hidden_dim=96)
        self.risk_head = AuxiliaryRegressionHead(hidden_dim=96)

    def forward(self, inputs: torch.Tensor) -> dict[str, torch.Tensor]:
        hidden = self.backbone(inputs)
        direction_logits = self.direction_head(hidden)
        risk_score = self.risk_head(hidden)
        return {
            "direction_logits": direction_logits,
            "direction_hidden": hidden,
            "opportunity_logit": self.opportunity_head(hidden),
            "tp_sl_logits": self.tp_sl_head(hidden),
            "expected_move_atr": self.move_head(hidden),
            "risk_score": risk_score,
            "invalidation_distance_atr": risk_score,
        }
