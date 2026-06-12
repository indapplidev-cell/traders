from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.training import training_pipeline_runner as runner_module
from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
)


def _candles() -> list[SimpleNamespace]:
    candles: list[SimpleNamespace] = []
    for index in range(36):
        candles.append(
            SimpleNamespace(
                open_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
                + timedelta(minutes=15 * index),
                open=100.0 + index,
                high=102.0 + index,
                low=99.0 + index,
                close=101.0 + index,
            )
        )
    return candles


class _SessionContext:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_ml36_1_runtime_regime_labels_are_built_and_used(monkeypatch) -> None:
    candles = _candles()
    feature_rows = [
        {
            "candle_open_time": candle.open_time,
            "features_json": {
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
            },
        }
        for candle in candles
    ]

    class FakeCandleRepository:
        def __init__(self, session: object) -> None:
            pass

        def get_all(self, *, symbol: str, interval: str) -> list[SimpleNamespace]:
            return candles

    class FakeFeatureRepository:
        def __init__(self, session: object) -> None:
            pass

        def get_all(self, *, symbol: str, interval: str, feature_version: str) -> list[dict]:
            return feature_rows

    class FakeLabelRepository:
        def __init__(self, session: object) -> None:
            pass

        def upsert_many(self, rows: list[dict]) -> int:
            return len(rows)

    monkeypatch.setattr(runner_module, "get_session", lambda: _SessionContext())
    monkeypatch.setattr(runner_module, "CandleRepository", FakeCandleRepository)
    monkeypatch.setattr(runner_module, "FeatureRepository", FakeFeatureRepository)
    monkeypatch.setattr(runner_module, "LabelRepository", FakeLabelRepository)

    runner = LongHistoryTrainingPipelineRunner()
    runner.DEFAULT_LABEL_VERSION = "lv2_h12_thr05_tp15_sl10"
    payload = runner._build_labels_real(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            feature_version="fv2",
        ),
        {},
    )

    status = payload["data"]["regime_label_builder_status"]
    assert payload["status"] == "COMPLETED"
    assert status["regime_label_builder_status"] == "built"
    assert status["regime_label_builder_used_in_training"] is True
    assert status["regime_specific_training_applied"] is True
    assert "regime_runtime_labels_not_built" not in status["missing_requirements"]


def test_ml36_1_runtime_regime_labels_block_pipeline_when_not_built(monkeypatch) -> None:
    candles = _candles()
    feature_rows = [
        {
            "candle_open_time": candle.open_time + timedelta(minutes=1),
            "features_json": {
                "regime_trend_up": 1.0,
                "regime_trend_down": 0.0,
                "regime_range": 0.0,
                "regime_high_volatility": 0.0,
                "regime_low_volatility": 1.0,
            },
        }
        for candle in candles
    ]

    class FakeCandleRepository:
        def __init__(self, session: object) -> None:
            pass

        def get_all(self, *, symbol: str, interval: str) -> list[SimpleNamespace]:
            return candles

    class FakeFeatureRepository:
        def __init__(self, session: object) -> None:
            pass

        def get_all(self, *, symbol: str, interval: str, feature_version: str) -> list[dict]:
            return feature_rows

    class FakeLabelRepository:
        def __init__(self, session: object) -> None:
            pass

        def upsert_many(self, rows: list[dict]) -> int:
            return len(rows)

    monkeypatch.setattr(runner_module, "get_session", lambda: _SessionContext())
    monkeypatch.setattr(runner_module, "CandleRepository", FakeCandleRepository)
    monkeypatch.setattr(runner_module, "FeatureRepository", FakeFeatureRepository)
    monkeypatch.setattr(runner_module, "LabelRepository", FakeLabelRepository)

    runner = LongHistoryTrainingPipelineRunner()
    runner.DEFAULT_LABEL_VERSION = "lv2_h12_thr05_tp15_sl10"
    payload = runner._build_labels_real(
        TrainingPipelineConfig(
            symbol="ETHUSDT",
            interval="15m",
            start_date="2025-01-01",
            feature_version="fv2",
        ),
        {},
    )

    status = payload["data"]["regime_label_builder_status"]
    assert payload["status"] == "FAILED"
    assert status["regime_label_builder_status"] == "blocked"
    assert status["regime_label_builder_used_in_training"] is False
    assert status["regime_specific_training_applied"] is False
    assert "regime_runtime_labels_not_built" in status["missing_requirements"]
