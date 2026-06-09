# Stage ML9 Report

## What Was Done
- Added prediction probability diagnostics for model output distribution.
- Added collapse detector v2 with dominant-class, no-signal and low-margin checks.
- Added signal gate evaluator v2 for `max_prob`, `directional_max_prob`, `margin`, `directional_edge`, `entropy`.
- Added profit-aware evaluation v2 with `profit_factor=null` for no-signal cases and optional `fee_r` / `slippage_r`.
- Added experiment summary v2 with recommendation rules that block collapsed or non-robust models.
- Added pytest coverage for all new ML9 rules.

## Created Files
- `app/diagnostics/prediction_probability_diagnostics.py`
- `app/diagnostics/prediction_collapse_detector.py`
- `app/evaluation/signal_gate_evaluator.py`
- `app/evaluation/profit_aware_evaluator_v2.py`
- `tests/test_prediction_probability_diagnostics.py`
- `tests/test_prediction_collapse_detector.py`
- `tests/test_signal_gate_evaluator.py`
- `tests/test_profit_aware_evaluator_v2.py`
- `tests/test_experiment_summary_v2.py`
- `reports/stage_ml9_signal_gating_profit_v2_report.md`

## Modified Files
- `app/diagnostics/diagnostics_service.py`
- `app/cli/commands.py`

## Pytest
- Command: `python -m pytest`
- Result: `55 passed`

## Final Checks
- `alembic upgrade head` -> success
- `python -m app.cli.commands health` -> `{"status": "ok", "service": "traders-ml", "version": "0.1.0"}`
- `python -m app.cli.commands db-check` -> `db-check: ok`
- For all 4 models executed:
- `probability-diagnostics`
- `signal-gate-eval`
- `profit-eval-v2`
- Executed:
- `python -m app.cli.commands experiment-summary-v2 --symbol BTCUSDT --interval 15m`

## Probability Diagnostics
- `ml_candle_mlp_v1_2026_06_08_172848`, `label_version=lv1`
- `dominant_class=UP`, `dominant_class_ratio=0.8835078534`
- `rows_above_0_45=0`
- `max_prob_q50=0.3629223257`, `max_prob_q90=0.3806547135`, `margin_q90=0.0646078378`
- `collapse_v2=true`, warnings: `no_signal_confidence_collapse`, `directional_bias_warning`
- `ml_candle_mlp_v1_2026_06_08_191038`, `label_version=lv_h16_thr03_tp10_sl10`
- `dominant_class=UP`, `dominant_class_ratio=0.9638157895`
- `rows_above_0_45=0`
- `max_prob_q50=0.3717887253`, `max_prob_q90=0.3900420278`, `margin_q90=0.0773349404`
- `collapse_v2=true`, warnings: `dominant_class_collapse`, `no_signal_confidence_collapse`, `directional_bias_warning`
- `ml_candle_mlp_v1_2026_06_08_191245`, `label_version=lv_h16_thr03_tp15_sl10`
- `dominant_class=UP`, `dominant_class_ratio=0.9671052632`
- `rows_above_0_45=0`
- `max_prob_q50=0.3770452589`, `max_prob_q90=0.3974349827`, `margin_q90=0.0888056397`
- `collapse_v2=true`, warnings: `dominant_class_collapse`, `no_signal_confidence_collapse`, `directional_bias_warning`
- `ml_candle_mlp_v1_2026_06_08_191453`, `label_version=lv_h16_thr03_tp20_sl10`
- `dominant_class=UP`, `dominant_class_ratio=0.9703947368`
- `rows_above_0_45=0`
- `max_prob_q50=0.3807283193`, `max_prob_q90=0.4045678139`, `margin_q90=0.0981192976`
- `collapse_v2=true`, warnings: `dominant_class_collapse`, `no_signal_confidence_collapse`, `directional_bias_warning`

## Signal Gate Eval
- Main diagnostic conclusion: threshold `0.45` produces zero signals because all 4 models have `rows_above_0_45=0` in probability diagnostics.
- Best gate by accuracy from `experiment-summary-v2`:
- `model_version=ml_candle_mlp_v1_2026_06_08_191453`
- `gate_type=entropy`
- `threshold=1.08`
- `signal_count=5`
- `accuracy_on_signals=1.0`
- `coverage=0.0032894737`
- This gate is not recommendation-worthy because signal count is too small.

## Profit Eval v2
- No-signal case no longer looks like `profit_factor=0.0`; it now returns `profit_factor=null`, `avg_r=null`, `expectancy_r=null`, `reject_reason=no_signals`.
- Best profit result by `profit_factor`:
- `model_version=ml_candle_mlp_v1_2026_06_08_191453`
- `gate_type=directional_edge`
- `threshold=0.15`
- `signal_count=8`
- `profit_factor=9.4138499806`
- `total_r=8.66626548`
- `expectancy_r=1.083283185`
- Best profit result by `total_r`:
- `model_version=ml_candle_mlp_v1_2026_06_08_191245`
- `gate_type=max_prob`
- `threshold=0.40`
- `signal_count=101`
- `profit_factor=1.5475368276`
- `total_r=25.51122144`
- `expectancy_r=0.2525863509`
- Base model `ml_candle_mlp_v1_2026_06_08_172848` also shows tradable low-threshold behaviour:
- best `gate_type=max_prob`, `threshold=0.40`
- `signal_count=18`
- `profit_factor=2.3248472748`
- `total_r=8.48511055`

## Recommendation Result
- `recommended_model_version=null`
- `recommended_gate_type=null`
- `recommended_gate_threshold=null`
- `recommended_label_version=null`
- Exact reason:
- profitable low-threshold gates now exist, but all candidate profitable ML8 models still fail collapse-v2 filters
- for `191038`, `191245`, `191453`: `collapse_detected=true` and `dominant_class_ratio >= 0.90`
- for `172848`: no `0.45+` confidence mass and it is not the best baseline-beating candidate
- `experiment-summary-v2` reject reasons:
- `collapse_detected`
- `dominant_class_ratio_gte_0_90`
- `expectancy_r_not_positive`
- `not_better_than_baseline`
- `profit_factor_is_null`
- `profit_factor_not_above_1`
- `signal_count_lt_50`
- `total_r_not_positive`

## Best Gate Types
- Highest signal accuracy: `entropy`, `threshold=1.08`, model `191453`, but only `5` signals.
- Highest profit factor: `directional_edge`, `threshold=0.15`, model `191453`, but only `8` signals.
- Highest total R: `max_prob`, `threshold=0.40`, model `191245`, with `101` signals and positive expectancy.
- Despite positive low-threshold profit metrics, recommendation remains blocked by collapse/bias rules.

## Constraints Confirmed
- No model was activated automatically.
- `model-activate` was not used.
- `traders-core` was not changed.
