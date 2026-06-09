from __future__ import annotations

from typing import Any

from app.db.repositories.candle_repository import CandleRepository
from app.db.repositories.feature_repository import FeatureRepository
from app.features.feature_builder import FeatureBuilder


class FeaturePipeline:
    def __init__(
        self,
        candle_repository: CandleRepository,
        feature_repository: FeatureRepository,
        feature_builder: FeatureBuilder | None = None,
    ) -> None:
        self._candle_repository = candle_repository
        self._feature_repository = feature_repository
        self._feature_builder = feature_builder or FeatureBuilder()

    def build_and_store(self, symbol: str, interval: str, feature_version: str) -> dict[str, Any]:
        candles = self._candle_repository.get_all(symbol=symbol, interval=interval)
        records = self._feature_builder.build(
            candles=candles,
            symbol=symbol,
            interval=interval,
            feature_version=feature_version,
        )
        inserted_or_updated = self._feature_repository.upsert_many([record.to_dict() for record in records])

        return {
            "symbol": symbol,
            "interval": interval,
            "feature_version": feature_version,
            "candles_used": len(candles),
            "built": len(records),
            "inserted_or_updated": inserted_or_updated,
            "first_open_time": records[0].candle_open_time.isoformat() if records else None,
            "last_open_time": records[-1].candle_open_time.isoformat() if records else None,
        }
