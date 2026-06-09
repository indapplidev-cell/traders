# Stage ML13 — Regime Segmentation and EMA Meta-Label Feasibility

## Что сделано

Добавлены:
- regime segmentation diagnostics для `fv2_regime`;
- walk-forward baseline by regime evaluator;
- EMA meta-label builder;
- meta-label diagnostics;
- meta dataset builder;
- meta baselines evaluator;
- optional meta-model training/evaluation/walk-forward flow;
- stage ML13 summary CLI.

Ключевой смысл этапа сохранён:
- MLP не использовался как замена EMA direction baseline;
- проверено, может ли ML выступать фильтром качества EMA-сигналов.

## Созданные файлы

- `app/diagnostics/regime_segment_diagnostics.py`
- `app/baseline/baseline_by_regime_evaluator.py`
- `app/meta_label/__init__.py`
- `app/meta_label/meta_label_models.py`
- `app/meta_label/ema_meta_label_builder.py`
- `app/meta_label/meta_dataset_builder.py`
- `app/meta_label/meta_baseline_evaluator.py`
- `app/meta_label/meta_training_service.py`
- `app/models/meta_mlp_model.py`
- `app/diagnostics/meta_label_diagnostics.py`
- `tests/test_regime_segment_diagnostics.py`
- `tests/test_baseline_by_regime_evaluator.py`
- `tests/test_ema_meta_label_builder.py`
- `tests/test_meta_label_diagnostics.py`
- `tests/test_meta_dataset_builder.py`
- `tests/test_meta_baseline_evaluator.py`
- `tests/test_stage_ml13_summary.py`
- `reports/stage_ml13_regime_meta_label_report.md`

## Изменённые файлы

- `app/diagnostics/diagnostics_service.py`
- `app/cli/commands.py`
- `app/models/model_factory.py`

## Проверки

- `python -m pytest` -> `88 passed`
- `alembic upgrade head` -> успешно
  Примечание: системный `alembic` снова указывал на Python 3.13; успешный прогон выполнен через Alembic из Python 3.11.
- `python -m app.cli.commands health` -> `{"status": "ok", "service": "traders-ml", "version": "0.1.0"}`
- `python -m app.cli.commands db-check` -> `db-check: ok`

Выполненные ML13 команды:
- `python -m app.cli.commands regime-segment-diagnostics --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp15_sl10 --take-profit-atr 1.5 --stop-loss-atr 1.0 --fee-r 0.02 --slippage-r 0.01 --same-candle-policy conservative`
- `python -m app.cli.commands baseline-by-regime --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp15_sl10 --mode expanding --train-days 45 --validation-days 10 --test-days 10 --step-days 10 --min-train-rows 1000 --take-profit-atr 1.5 --stop-loss-atr 1.0 --fee-r 0.02 --slippage-r 0.01 --same-candle-policy conservative`
- `python -m app.cli.commands build-ema-meta-labels --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version meta_ema_9_21_tp15_sl10 --take-profit-atr 1.5 --stop-loss-atr 1.0 --fee-r 0.02 --slippage-r 0.01 --same-candle-policy conservative`
- `python -m app.cli.commands meta-label-diagnostics --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version meta_ema_9_21_tp15_sl10`
- `python -m app.cli.commands build-meta-dataset --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version meta_ema_9_21_tp15_sl10`
- `python -m app.cli.commands meta-baselines --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version meta_ema_9_21_tp15_sl10 --mode expanding --train-days 45 --validation-days 10 --test-days 10 --step-days 10 --min-train-rows 1000`
- `python -m app.cli.commands train-meta --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version meta_ema_9_21_tp15_sl10`
- `python -m app.cli.commands evaluate-meta --model-version ema_meta_mlp_v1_2026_06_09_050110`
- `python -m app.cli.commands walk-forward-meta-eval --model-version ema_meta_mlp_v1_2026_06_09_050110 --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version meta_ema_9_21_tp15_sl10 --mode expanding --train-days 45 --validation-days 10 --test-days 10 --step-days 10 --min-train-rows 1000 --threshold-grid 0.50,0.55,0.60,0.65,0.70`
- `python -m app.cli.commands stage-ml13-summary --symbol BTCUSDT --interval 15m`

## Regime Segment Diagnostics

Отчёт:
- `reports/regime_segment_diagnostics_BTCUSDT_15m_fv2_regime.json`

Где EMA baseline работает по сегментной диагностике:
- `regime_trend_down`
- `regime_low_volatility`
- `regime_volatility_contracting`
- `ema_stack_bearish`
- `close_below_ema_200`

Где EMA baseline проваливается по сегментной диагностике:
- `regime_trend_up`
- `regime_range`
- `regime_high_volatility`
- `regime_volatility_expanding`
- `ema_stack_bullish`
- `close_above_ema_200`

Где есть directional edge:
- long edge: `regime_trend_up`, `regime_range`, `regime_low_volatility`, `regime_volatility_contracting`, `close_above_ema_200`
- short edge: `regime_trend_down`, `regime_high_volatility`, `regime_volatility_expanding`, `ema_stack_bullish`, `ema_stack_bearish`, `close_below_ema_200`

## Baseline By Regime

Отчёт:
- `reports/baseline_by_regime_BTCUSDT_15m_fv2_regime.json`

Best baseline overall:
- `ema_9_21_direction`
- `total_r = 129.6027191899973`
- `profit_factor = 1.0723524923111214`

Best baseline by regime:
- `regime_trend_up` -> `ema_21_50_direction`
- `regime_trend_down` -> `ema_stack_direction`
- `regime_range` -> `ema_9_21_direction`
- `regime_high_volatility` -> `ema_stack_direction`
- `regime_low_volatility` -> `ema_9_21_direction`
- `regime_volatility_expanding` -> `ema_stack_direction`
- `regime_volatility_contracting` -> `always_long`
- `ema_stack_bullish` -> `ema_9_21_direction`
- `ema_stack_bearish` -> `ema_9_21_direction`
- `close_above_ema_200` -> `ema_stack_direction`
- `close_below_ema_200` -> `ema_9_21_direction`

## EMA Meta Labels

Отчёт:
- `reports/ema_meta_labels_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json`

Статистика:
- `total_rows = 8604`
- `ema_long_count = 4122`
- `ema_short_count = 3960`
- `ema_flat_count = 522`
- `meta_win_count = 3235`
- `meta_loss_count = 4466`
- `ambiguous_count = 0`
- `no_exit_count = 381`
- `no_trade_count = 522`
- `win_rate = 0.4200753148941696`
- `long_win_rate = 0.428023523395551`
- `short_win_rate = 0.4118733509234829`
- `avg_meta_trade_r = 0.0240950215191419`
- `total_meta_trade_r = 194.73596391770485`

## Meta Label Diagnostics

Отчёт:
- `reports/meta_label_diagnostics_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json`

Результат:
- warnings отсутствуют
- top WIN/LOSS separation features:
  `ema_21`, `ema_9`, `ema_50`, `ema_200`, `macd_signal`

## Meta Dataset

Отчёт:
- `reports/meta_dataset_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json`

Результат:
- `meta_dataset_valid = true`
- `dataset_rows = 7521`
- `train_rows = 5264`
- `validation_rows = 1128`
- `test_rows = 1129`
- `positive_class_ratio = 0.41896024464831805`
- `negative_class_ratio = 0.581039755351682`
- `long_rows = 3776`
- `short_rows = 3745`
- `excluded_no_trade = 522`
- `excluded_ambiguous = 0`
- `excluded_no_exit = 381`

## Meta Baselines

Отчёт:
- `reports/meta_baselines_BTCUSDT_15m_meta_ema_9_21_tp15_sl10.json`

Ключевые результаты:
- `take_all_ema_signals`:
  `signal_count = 2827`
  `total_r = 108.18999999999748`
  `profit_factor = inf`
  `profitable_fold_ratio = 1.0`
- best meta baseline overall:
  `take_all_ema_signals`

## Meta Model

Обучена ровно 1 meta-model:
- `ema_meta_mlp_v1_2026_06_09_050110`

Artifact:
- `artifacts/models/ema_meta_mlp_v1_2026_06_09_050110`

Evaluation:
- `test accuracy = 0.5376439094543457`
- `test precision = 0.3561643835616438`
- `test recall = 0.05189620758483034`
- `test brier_score = 0.25537633895874023`

Walk-forward meta eval:
- `selected threshold dominant = 0.5`
- `total_test_signal_count = 245`
- `global_total_r = 60.149999999999885`
- `global_profit_factor = 6.0334728033472675`
- `global_expectancy_r = 0.24551020408163218`
- `long_total_count = 240`
- `short_total_count = 5`
- `profitable_fold_ratio = 0.5`

Сравнение с `take_all_ema_signals`:
- meta-model лучше по `profit_factor`
- meta-model хуже по `global_total_r`
- meta-model не может быть рекомендована по правилу этапа

## Итог ML13

- `recommended_model_version = null`
- точные reject reasons:
  - `meta_model_not_above_take_all_ema`
  - `profitable_fold_ratio_lt_0_60`
- `recommended_next_action = improve_meta_features`

## Подтверждения

- Модель не активировалась.
- `model-activate` не запускался.
- `traders-core` не изменялся.
