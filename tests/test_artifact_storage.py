from pathlib import Path

import torch

from app.models.mlp_model import CandleMLP
from app.registry.artifact_storage import ArtifactStorage


def test_artifact_storage_writes_required_files(tmp_path: Path) -> None:
    storage = ArtifactStorage(base_dir=tmp_path)
    model = CandleMLP(input_dim=34)

    output_path = storage.save(
        model_version="ml_candle_mlp_v1_2026_06_08_010203",
        model=model,
        scaler={"mean": [0.0] * 34, "std": [1.0] * 34},
        feature_columns=[f"f_{index}" for index in range(34)],
        training_config={"model_name": "candle_mlp"},
        metrics={"test": {"accuracy": 0.5}},
    )

    assert Path(output_path).exists()
    assert storage.exists("ml_candle_mlp_v1_2026_06_08_010203") is True
