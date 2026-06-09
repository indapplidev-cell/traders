from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from pathlib import Path

from app.replay.historical_replay_engine import HistoricalReplayEngine


def test_replay_engine_runs_and_persists_results(tmp_path: Path) -> None:
    candles = _build_candles(220)
    replay_repository = FakeReplayRepository()
    engine = HistoricalReplayEngine(
        candle_repository=FakeCandleRepository(candles),
        predictor=FakePredictor(),
        replay_repository=replay_repository,
        reports_dir=tmp_path,
    )

    result = engine.run(
        model_version="mv1",
        symbol="BTCUSDT",
        interval="15m",
        start_at=datetime(2025, 1, 3, tzinfo=timezone.utc),
        end_at=datetime(2025, 1, 4, tzinfo=timezone.utc),
        horizon_candles=2,
    )

    assert result["results_written"] > 0
    assert replay_repository.session_updates
    assert Path(result["metrics"]["report_path"]).exists()


class FakeCandleRepository:
    def __init__(self, candles):
        self._candles = candles

    def get_all(self, symbol: str, interval: str):
        return list(self._candles)


class FakePredictor:
    def predict(self, **kwargs):
        return {
            "ml_available": True,
            "direction": "UP",
            "prob_up": 0.7,
            "prob_down": 0.2,
            "prob_flat": 0.1,
        }


class FakeReplayRepository:
    def __init__(self) -> None:
        self.sessions = {}
        self.results = []
        self.session_updates = []

    def create_session(self, payload):
        self.sessions[payload["session_id"]] = payload
        return payload

    def add_results(self, payloads):
        self.results.extend(payloads)
        return len(payloads)

    def update_session(self, session_id, **values):
        self.session_updates.append((session_id, values))


def _build_candles(count: int):
    candles = []
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        price = 100 + index * 0.1
        candles.append(
            SimpleNamespace(
                open_time=start_at + timedelta(minutes=15 * index),
                open=price,
                high=price + 2,
                low=price - 1,
                close=price + 0.5,
                volume=1000 + index,
                taker_buy_base_volume=500 + index,
            )
        )
    return candles
