from types import SimpleNamespace

from app.registry.model_registry import ModelRegistry


def test_model_registry_activation_deactivates_scope_and_returns_warning() -> None:
    repository = FakeModelRegistryRepository()
    registry = ModelRegistry(repository=repository, artifact_storage=FakeArtifactStorage(exists=True))

    result = registry.activate("ml_candle_mlp_v1_2026_06_08_010203")

    assert result["activated"] is True
    assert result["warning"] is not None
    assert repository.deactivated_scope == ("BTCUSDT", "15m", 8)
    assert repository.activated_model_version == "ml_candle_mlp_v1_2026_06_08_010203"


class FakeArtifactStorage:
    def __init__(self, exists: bool) -> None:
        self._exists = exists

    def exists(self, model_version: str) -> bool:
        return self._exists


class FakeModelRegistryRepository:
    def __init__(self) -> None:
        self.deactivated_scope = None
        self.activated_model_version = None

    def get_by_model_version(self, model_version: str):
        return SimpleNamespace(
            model_version=model_version,
            symbol="BTCUSDT",
            interval="15m",
            horizon_candles=8,
            accuracy=0.2,
            brier_score=0.9,
        )

    def deactivate_scope(self, symbol: str, interval: str, horizon_candles: int) -> None:
        self.deactivated_scope = (symbol, interval, horizon_candles)

    def set_active(self, model_version: str, is_active: bool) -> None:
        if is_active:
            self.activated_model_version = model_version
