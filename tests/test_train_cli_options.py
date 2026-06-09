from app.cli import commands


def test_train_cli_options_are_forwarded(monkeypatch) -> None:
    captured = {}

    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeService:
        def train(self, **kwargs):
            captured.update(kwargs)
            return {"ok": True}

    monkeypatch.setattr(commands, "get_session", lambda: FakeSession())
    monkeypatch.setattr(commands, "FeatureRepository", lambda session: object())
    monkeypatch.setattr(commands, "LabelRepository", lambda session: object())
    monkeypatch.setattr(commands, "DatasetBuilder", lambda **kwargs: object())
    monkeypatch.setattr(commands, "ArtifactStorage", lambda: object())
    monkeypatch.setattr(commands, "ModelRegistryRepository", lambda session: object())
    monkeypatch.setattr(commands, "TrainingRunRepository", lambda session: object())
    monkeypatch.setattr(commands, "ModelRegistry", lambda **kwargs: object())
    monkeypatch.setattr(commands, "TrainingService", lambda **kwargs: FakeService())

    commands.train_command(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv1",
        label_version="lv1",
        model_name="candle_mlp",
        epochs=3,
        learning_rate=0.005,
        weight_decay=0.01,
        train_end="2025-03-01",
        validation_end="2025-03-16",
        disable_class_weights=True,
    )

    assert captured["epochs"] == 3
    assert captured["learning_rate"] == 0.005
    assert captured["weight_decay"] == 0.01
    assert captured["train_end"].isoformat() == "2025-03-01"
    assert captured["validation_end"].isoformat() == "2025-03-16"
    assert captured["disable_class_weights"] is True


def test_train_cli_resolves_horizon_and_default_model_name_from_label_version(monkeypatch) -> None:
    captured = {}

    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeService:
        def train(self, **kwargs):
            captured.update(kwargs)
            return {"ok": True}

    monkeypatch.setattr(commands, "get_session", lambda: FakeSession())
    monkeypatch.setattr(commands, "FeatureRepository", lambda session: object())
    monkeypatch.setattr(commands, "LabelRepository", lambda session: object())
    monkeypatch.setattr(commands, "DatasetBuilder", lambda **kwargs: object())
    monkeypatch.setattr(commands, "ArtifactStorage", lambda: object())
    monkeypatch.setattr(commands, "ModelRegistryRepository", lambda session: object())
    monkeypatch.setattr(commands, "TrainingRunRepository", lambda session: object())
    monkeypatch.setattr(commands, "ModelRegistry", lambda **kwargs: object())
    monkeypatch.setattr(commands, "TrainingService", lambda **kwargs: FakeService())

    commands.train_command(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=None,
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp15_sl10",
        model_name="candle_mlp",
        train_end=None,
        validation_end=None,
    )

    assert captured["horizon_candles"] == 16
    assert captured["model_name"] == "candle_mlp"


def test_build_dataset_cli_resolves_horizon_from_label_version(monkeypatch) -> None:
    captured = {}

    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeBuilder:
        def build(self, **kwargs):
            captured.update(kwargs)
            return {"ok": True}

    monkeypatch.setattr(commands, "get_session", lambda: FakeSession())
    monkeypatch.setattr(commands, "FeatureRepository", lambda session: object())
    monkeypatch.setattr(commands, "LabelRepository", lambda session: object())
    monkeypatch.setattr(commands, "DatasetBuilder", lambda **kwargs: FakeBuilder())

    commands.build_dataset_command(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=None,
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp10_sl10",
        train_end=None,
        validation_end=None,
    )

    assert captured["horizon_candles"] == 16
