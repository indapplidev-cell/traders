from datetime import datetime, timezone
from types import SimpleNamespace

from app.dataset.dataset_builder import DatasetBuilder


class _FeatureRepository:
    def get_all(self, symbol: str, interval: str, feature_version: str):
        return [
            SimpleNamespace(
                symbol=symbol,
                interval=interval,
                candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                feature_version=feature_version,
                features_json={
                    "return_1": 0.01,
                    "ema_9": 10.0,
                    "ema_21": 9.5,
                    "near_support": True,
                    "support_distance_atr": 0.12,
                    "resistance_distance_atr": 1.20,
                    "nison_bullish_engulfing": 0.90,
                    "regime_trend_up": 1.0,
                },
            ),
            SimpleNamespace(
                symbol=symbol,
                interval=interval,
                candle_open_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
                feature_version=feature_version,
                features_json={
                    "return_1": 0.0,
                    "ema_9": 10.0,
                    "ema_21": 10.0,
                    "support_distance_atr": 2.0,
                    "resistance_distance_atr": 2.0,
                    "regime_range": 1.0,
                },
            ),
        ]


class _LabelRepository:
    def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
        return [
            SimpleNamespace(
                symbol=symbol,
                interval=interval,
                candle_open_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                horizon_candles=horizon_candles,
                label_version=label_version,
                direction_label="UP",
                tp_before_sl=True,
                future_return=0.02,
                future_move_atr=0.85,
                max_favorable_move_atr=1.10,
                max_adverse_move_atr=0.20,
            ),
            SimpleNamespace(
                symbol=symbol,
                interval=interval,
                candle_open_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
                horizon_candles=horizon_candles,
                label_version=label_version,
                direction_label="FLAT",
                tp_before_sl=None,
                future_return=0.0,
                future_move_atr=0.05,
                max_favorable_move_atr=0.10,
                max_adverse_move_atr=0.08,
            ),
        ]


def test_opportunity_fields_are_attached_to_dataset_rows() -> None:
    rows, summary = DatasetBuilder(
        feature_repository=_FeatureRepository(),
        label_repository=_LabelRepository(),
    ).build_rows(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv4_book_setup_context",
        label_version="lv13_h12_opportunity_ft",
    )

    assert len(rows) == 2
    assert rows[0].opportunity_label == 1
    assert rows[0].opportunity_direction == "UP"
    assert rows[0].setup_type != "no_setup"
    assert rows[0].setup_expected_move_atr > 0.0
    assert rows[1].opportunity_label == 0
    assert "opportunity_rows" in summary
    assert summary["opportunity_rows"] == 1
    assert summary["no_trade_rows"] == 1


def test_dataset_builder_prefers_persisted_opportunity_fields_when_available() -> None:
    class _FeatureRepositoryWithoutSetup:
        def get_all(self, symbol: str, interval: str, feature_version: str):
            return [
                SimpleNamespace(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
                    feature_version=feature_version,
                    features_json={
                        "return_1": 0.0,
                        "ema_9": 10.0,
                        "ema_21": 10.0,
                        "support_distance_atr": 2.0,
                        "resistance_distance_atr": 2.0,
                        "regime_range": 1.0,
                    },
                )
            ]

    class _PersistedOpportunityLabelRepository:
        def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
            return [
                SimpleNamespace(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
                    horizon_candles=horizon_candles,
                    label_version=label_version,
                    direction_label="UP",
                    tp_before_sl=True,
                    future_return=0.02,
                    future_move_atr=0.90,
                    max_favorable_move_atr=1.20,
                    max_adverse_move_atr=0.25,
                    opportunity_label=1,
                    opportunity_direction="UP",
                    opportunity_reason="persisted_test_payload",
                    opportunity_score=0.91,
                    setup_type="persisted_setup",
                    setup_quality_score=0.88,
                    setup_invalidation_distance_atr=0.22,
                    setup_expected_move_atr=1.15,
                    label_ambiguity_score=0.12,
                )
            ]

    rows, summary = DatasetBuilder(
        feature_repository=_FeatureRepositoryWithoutSetup(),
        label_repository=_PersistedOpportunityLabelRepository(),
    ).build_rows(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv4_book_setup_context",
        label_version="lv13_h12_opportunity_ft",
    )

    assert len(rows) == 1
    assert rows[0].opportunity_label == 1
    assert rows[0].opportunity_direction == "UP"
    assert rows[0].opportunity_reason == "persisted_test_payload"
    assert rows[0].opportunity_score == 0.91
    assert rows[0].setup_type == "persisted_setup"
    assert rows[0].setup_quality_score == 0.88
    assert rows[0].setup_invalidation_distance_atr == 0.22
    assert rows[0].setup_expected_move_atr == 1.15
    assert rows[0].label_ambiguity_score == 0.12
    assert summary["opportunity_rows"] == 1
    assert summary["no_trade_rows"] == 0

def test_dataset_builder_prefers_persisted_opportunity_fields() -> None:
    class _PersistedFeatureRepository:
        def get_all(self, symbol: str, interval: str, feature_version: str):
            return [
                SimpleNamespace(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
                    feature_version=feature_version,
                    features_json={
                        "return_1": 0.0,
                        "ema_9": 10.0,
                        "ema_21": 10.0,
                        "support_distance_atr": 2.0,
                        "resistance_distance_atr": 2.0,
                        "regime_range": 1.0,
                    },
                )
            ]

    class _PersistedLabelRepository:
        def get_all(self, symbol: str, interval: str, horizon_candles: int, label_version: str):
            return [
                SimpleNamespace(
                    symbol=symbol,
                    interval=interval,
                    candle_open_time=datetime(2025, 1, 3, tzinfo=timezone.utc),
                    horizon_candles=horizon_candles,
                    label_version=label_version,
                    direction_label="FLAT",
                    tp_before_sl=None,
                    future_return=0.0,
                    future_move_atr=0.05,
                    max_favorable_move_atr=0.10,
                    max_adverse_move_atr=0.08,
                    opportunity_label=1,
                    opportunity_direction="UP",
                    opportunity_reason="persisted_test_payload",
                    opportunity_score=0.91,
                    setup_type="persisted_setup",
                    setup_quality_score=0.88,
                    setup_invalidation_distance_atr=0.22,
                    setup_expected_move_atr=0.67,
                    label_ambiguity_score=0.11,
                )
            ]

    rows, summary = DatasetBuilder(
        feature_repository=_PersistedFeatureRepository(),
        label_repository=_PersistedLabelRepository(),
    ).build_rows(
        symbol="BTCUSDT",
        interval="15m",
        horizon_candles=8,
        feature_version="fv4_book_setup_context",
        label_version="lv13_h12_opportunity_ft",
    )

    assert len(rows) == 1
    assert rows[0].opportunity_label == 1
    assert rows[0].opportunity_direction == "UP"
    assert rows[0].opportunity_reason == "persisted_test_payload"
    assert rows[0].opportunity_score == 0.91
    assert rows[0].setup_type == "persisted_setup"
    assert rows[0].setup_quality_score == 0.88
    assert rows[0].setup_invalidation_distance_atr == 0.22
    assert rows[0].setup_expected_move_atr == 0.67
    assert rows[0].label_ambiguity_score == 0.11
    assert summary["opportunity_rows"] == 1
    assert summary["no_trade_rows"] == 0