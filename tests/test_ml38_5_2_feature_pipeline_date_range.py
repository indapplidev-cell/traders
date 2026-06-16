from datetime import datetime, timezone
from types import SimpleNamespace

from app.features.feature_pipeline import FeaturePipeline


def test_feature_pipeline_uses_candle_range_when_provided() -> None:
    candle_repo = FakeCandleRepository()
    feature_repo = FakeFeatureRepository()
    pipeline = FeaturePipeline(
        candle_repository=candle_repo,
        feature_repository=feature_repo,
        feature_builder=FakeFeatureBuilder(),
    )

    start_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    end_at = datetime(2026, 6, 16, tzinfo=timezone.utc)

    result = pipeline.build_and_store(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv3_candle_ta_context",
        start_at=start_at,
        end_at=end_at,
    )

    assert candle_repo.get_range_called is True
    assert candle_repo.get_all_called is False
    assert result["candles_used"] == 2
    assert result["built"] == 2
    assert result["date_range_limited"] is True
    assert result["start_at"] == start_at.isoformat()
    assert result["end_at"] == end_at.isoformat()


class FakeCandleRepository:
    def __init__(self) -> None:
        self.get_range_called = False
        self.get_all_called = False

    def get_range(self, **kwargs):
        self.get_range_called = True
        return [
            SimpleNamespace(open_time=datetime(2026, 5, 1, tzinfo=timezone.utc)),
            SimpleNamespace(open_time=datetime(2026, 5, 2, tzinfo=timezone.utc)),
        ]

    def get_all(self, **kwargs):
        self.get_all_called = True
        return []


class FakeFeatureRepository:
    def __init__(self) -> None:
        self.rows = []

    def upsert_many(self, rows):
        self.rows = list(rows)
        return len(rows)


class FakeFeatureBuilder:
    def build(self, candles, symbol, interval, feature_version):
        return [
            SimpleNamespace(
                candle_open_time=item.open_time,
                to_dict=lambda item=item: {
                    "symbol": symbol,
                    "interval": interval,
                    "candle_open_time": item.open_time,
                    "feature_version": feature_version,
                    "features_json": {"atr_14": 1.0},
                },
            )
            for item in candles
        ]
