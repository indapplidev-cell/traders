from __future__ import annotations

import torch
from torch import nn


class CandleMLP(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
        )
        self.direction_head = nn.Linear(64, 3)
        self.tp_sl_head = nn.Linear(64, 1)
        self.move_head = nn.Linear(64, 1)
        self.risk_head = nn.Linear(64, 1)

    def forward(self, inputs: torch.Tensor) -> dict[str, torch.Tensor]:
        hidden = self.backbone(inputs)
        return {
            "direction_logits": self.direction_head(hidden),
            "tp_sl_logits": self.tp_sl_head(hidden).squeeze(-1),
            "expected_move_atr": self.move_head(hidden).squeeze(-1),
            "risk_score": self.risk_head(hidden).squeeze(-1),
        }
