from __future__ import annotations

from app.models.mlp_model import CandleMLP
from app.models.meta_mlp_model import EmaMetaMLP


class ModelFactory:
    def create(self, model_name: str, input_dim: int):
        if model_name == "candle_mlp":
            return CandleMLP(input_dim=input_dim)
        if model_name == "ema_meta_mlp_v1":
            return EmaMetaMLP(input_dim=input_dim)
        raise ValueError(f"Unsupported model_name: {model_name}")
