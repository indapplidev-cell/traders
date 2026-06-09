# Stage ML3 Features Labels Dataset Report

## Created Files

- `app/features/__init__.py`
- `app/features/feature_models.py`
- `app/features/technical_indicators.py`
- `app/features/feature_builder.py`
- `app/features/feature_pipeline.py`
- `app/labels/__init__.py`
- `app/labels/label_models.py`
- `app/labels/direction_label_builder.py`
- `app/labels/tp_sl_label_builder.py`
- `app/labels/label_builder.py`
- `app/dataset/__init__.py`
- `app/dataset/dataset_models.py`
- `app/dataset/dataset_builder.py`
- `app/dataset/dataset_splitter.py`
- `app/dataset/dataset_exporter.py`
- `app/db/repositories/feature_repository.py`
- `app/db/repositories/label_repository.py`
- `alembic/versions/0002_make_tp_before_sl_nullable.py`
- `tests/test_technical_indicators.py`
- `tests/test_feature_builder.py`
- `tests/test_label_builder.py`
- `tests/test_dataset_splitter.py`
- `tests/test_dataset_builder.py`
- `reports/stage_ml3_features_labels_dataset_report.md`
- `reports/dataset_summary_btcusdt_15m_h8_fv1_lv1.json`

## Changed Files

- `app/cli/commands.py`
- `app/db/models.py`
- `app/db/repositories/__init__.py`
- `app/db/repositories/candle_repository.py`
- `alembic/versions/0001_ml_foundation.py`

## Feature List

- `body_size`
- `upper_wick`
- `lower_wick`
- `candle_range`
- `body_to_range_ratio`
- `close_position_in_range`
- `return_1`
- `return_3`
- `return_5`
- `return_10`
- `log_return_1`
- `atr_14`
- `atr_28`
- `range_percent`
- `rolling_volatility_20`
- `rolling_volatility_50`
- `ema_9`
- `ema_21`
- `ema_50`
- `ema_200`
- `close_to_ema_9`
- `close_to_ema_21`
- `close_to_ema_50`
- `ema_9_to_ema_21`
- `ema_21_to_ema_50`
- `trend_strength`
- `rsi_14`
- `macd`
- `macd_signal`
- `macd_histogram`
- `volume_sma_20`
- `volume_ratio_20`
- `volume_spike`
- `taker_buy_ratio`

## Label List

- `direction_label`
- `tp_before_sl`
- `future_return`
- `future_move_atr`
- `max_favorable_move_atr`
- `max_adverse_move_atr`

Direction rule:
- `future_return > 0.5 * ATR / current_close` -> `UP`
- `future_return < -0.5 * ATR / current_close` -> `DOWN`
- otherwise -> `FLAT`

TP/SL rule:
- Long:
  - `take_profit = current_close + 1.5 * ATR`
  - `stop_loss = current_close - 1.0 * ATR`
- Short:
  - `take_profit = current_close - 1.5 * ATR`
  - `stop_loss = current_close + 1.0 * ATR`

## Future Leak Protection

- `FeatureBuilder` использует только текущую и прошлые свечи:
  - returns рассчитываются только по lookback-окнам
  - ATR, EMA, RSI, MACD, volatility и volume SMA считаются только из истории до текущей свечи включительно
  - будущие свечи не участвуют в `features_json`
- `LabelBuilder` разделяет прошлое и будущее:
  - ATR для threshold и TP/SL берётся только на текущей свече из прошлого окна
  - label считается только по окну `candles[i+1 : i+1+horizon_candles]`
  - свечи после этого future window не влияют на label
- `DatasetSplitter` делает только time-based split:
  - `train` `< 2025-11-01`
  - `validation` `>= 2025-11-01` and `< 2026-03-01`
  - `test` `>= 2026-03-01`
- `DatasetBuilder` исключает строки с неполными indicators и строки без label до split.

## Verification Commands

- `python -m pytest`
- `python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv1`
- `python -m app.cli.commands build-labels --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1`
- `python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1`

## Verification Results

- `python -m pytest`
  - `16 passed`
- `python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv1`
  - `candles_used: 192`
  - `built: 192`
  - `inserted_or_updated: 192`
  - `first_open_time: 2025-01-01T00:00:00+00:00`
  - `last_open_time: 2025-01-02T23:45:00+00:00`
- `python -m app.cli.commands build-labels --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1`
  - `candles_used: 192`
  - `built: 171`
  - `inserted_or_updated: 171`
  - `direction_counts: UP=87, DOWN=35, FLAT=49`
  - `first_open_time: 2025-01-01T03:15:00+00:00`
  - `last_open_time: 2025-01-02T21:45:00+00:00`
- `python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1`
  - `feature_rows: 192`
  - `label_rows: 171`
  - `dataset_rows: 0`
  - `dropped_incomplete_features: 192`
  - `train_rows: 0`
  - `validation_rows: 0`
  - `test_rows: 0`
  - `summary_path: reports/dataset_summary_btcusdt_15m_h8_fv1_lv1.json`

Notes:
- Before final checks the Alembic migration `0002_make_tp_before_sl_nullable` was applied so `ml_labels.tp_before_sl` can store `null`.
- With the currently loaded BTCUSDT history only `192` candles are available, so all dataset rows are dropped as incomplete because `ema_200` cannot be fully formed yet.
