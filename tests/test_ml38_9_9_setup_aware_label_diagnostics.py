from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.diagnostics.setup_aware_label_diagnostics import SetupAwareLabelDiagnostics
from app.labels.label_builder import LabelBuilder
from app.labels.label_config import LabelConfig, LABEL_MODE_SETUP_AWARE_FIRST_TOUCH


def test_setup_aware_label_diagnostics_reports_no_setup_group() -> None:
    payload = SetupAwareLabelDiagnostics().evaluate(
        [
            {
                "setup_type": "no_setup",
                "future_close_atr_label": "FLAT",
                "first_touch_tp_sl_label": "UP",
                "setup_aware_first_touch_label": "FLAT",
                "future_move_atr": 0.4,
                "first_touch_ambiguous": False,
                "has_setup_context": False,
            }
        ]
    )

    assert payload["row_count_by_setup_type"]["no_setup"] == 1
    assert "no_setup" in payload["recommended_label_mode_by_setup_type"]


def test_setup_aware_label_builder_does_not_crash_when_setup_features_are_absent() -> None:
    candles = _build_candles()
    records = LabelBuilder().build(
        candles=candles,
        symbol="SOLUSDT",
        interval="15m",
        horizon_candles=2,
        label_version="lv12_h12_setup_ft_tp12_sl12",
        config=LabelConfig(
            label_version="lv12_h12_setup_ft_tp12_sl12",
            horizon_candles=2,
            direction_atr_threshold=0.6,
            take_profit_atr=1.2,
            stop_loss_atr=1.2,
            flat_class_enabled=True,
            label_mode=LABEL_MODE_SETUP_AWARE_FIRST_TOUCH,
        ),
        feature_rows=[],
    )

    assert records


def _build_candles() -> list[SimpleNamespace]:
    start_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    candles: list[SimpleNamespace] = []
    prices = [100.0, 100.4, 100.1, 100.6, 100.2, 100.5, 100.3, 100.7, 100.4, 100.8, 100.5, 100.9, 100.6, 101.0, 100.7, 101.1]
    for index, close_price in enumerate(prices):
        candles.append(
            SimpleNamespace(
                open_time=start_at + timedelta(minutes=index * 15),
                open=close_price - 0.2,
                high=close_price + 0.5,
                low=close_price - 0.5,
                close=close_price,
                volume=100.0,
                taker_buy_base_volume=55.0,
            )
        )
    return candles
