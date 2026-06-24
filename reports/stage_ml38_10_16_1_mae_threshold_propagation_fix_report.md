# ML38.10.16.1 — MAE threshold propagation fix

## Status
Implemented / research-only.

## Problem
ML38.10.16 added `mae_pressure_max_risk_score` to lv24 configs and final-stream diagnostics, but runtime archives showed that the threshold did not reach the actual final-stream filter:

- label config MAE threshold: `0.55` / `0.52`
- audit MAE threshold: `1.0`
- high MAE pressure blocks: `0`

This meant the MAE-aware gate was effectively disabled by default fallback.

## Fix
Propagated `mae_pressure_max_risk_score` through:

- `TrainingPipelineConfig`
- `TrainingService.TrainingConfig`
- `Evaluator.evaluate()`
- `TrainingMetrics.compute()`
- persisted `training_config.json`
- label-grid candidate result payloads
- feature-regime candidate result payloads
- multi-symbol summaries and reports

## Acceptance rule
For lv24 runtime candidates the audit must show:

- `label_config.mae_pressure_max_risk_score = 0.55 / 0.52`
- `entry_path_prediction_filter_summary.mae_pressure_threshold = 0.55 / 0.52`
- `stop_pressure_effectiveness_audit.mae_pressure_threshold = 0.55 / 0.52`
- `blocked_by_high_mae_pressure_count > 0` when MAE pressure actually exceeds threshold

## Safety
- live trading: disabled
- orders: disabled
- auto activation: disabled
- research-only: yes
