from __future__ import annotations

from datetime import datetime
from typing import Any


class ReplayService:
    def __init__(self, replay_engine, replay_repository, model_registry_repository) -> None:
        self._replay_engine = replay_engine
        self._replay_repository = replay_repository
        self._model_registry_repository = model_registry_repository

    def replay(
        self,
        symbol: str,
        interval: str,
        start_at: datetime,
        end_at: datetime,
        horizon_candles: int,
        model_version: str | None = None,
    ) -> dict[str, Any]:
        selected_model_version = model_version
        if selected_model_version is None:
            active_model = self._model_registry_repository.get_active_model(
                symbol=symbol,
                interval=interval,
                horizon_candles=horizon_candles,
            )
            if active_model is None:
                raise ValueError("Active model not found.")
            selected_model_version = active_model.model_version

        return self._replay_engine.run(
            model_version=selected_model_version,
            symbol=symbol,
            interval=interval,
            start_at=start_at,
            end_at=end_at,
            horizon_candles=horizon_candles,
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._replay_repository.list_sessions()
