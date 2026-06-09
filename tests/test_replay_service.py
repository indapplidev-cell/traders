from datetime import datetime, timezone

from app.replay.replay_service import ReplayService


def test_replay_service_resolves_active_model_when_missing() -> None:
    service = ReplayService(
        replay_engine=FakeReplayEngine(),
        replay_repository=FakeReplayRepository(),
        model_registry_repository=FakeModelRegistryRepository(),
    )

    result = service.replay(
        symbol="BTCUSDT",
        interval="15m",
        start_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
        horizon_candles=8,
        model_version=None,
    )

    assert result["model_version"] == "mv_active"
    assert service.list_sessions() == [{"session_id": "s1"}]


class FakeReplayEngine:
    def run(self, **kwargs):
        return {"model_version": kwargs["model_version"]}


class FakeReplayRepository:
    def list_sessions(self):
        return [{"session_id": "s1"}]


class FakeModelRegistryRepository:
    def get_active_model(self, symbol: str, interval: str, horizon_candles: int):
        return type("ModelRow", (), {"model_version": "mv_active"})()
