# Stage ML36.1 Report

## What Was Broken After The Fresh BTC/ETH/SOL Grid

- The fresh BTC/ETH/SOL feature-regime grid still showed `regime_label_builder_used_in_training=false`.
- The summaries still showed `regime_specific_training_applied=false`.
- The runtime failure marker was `missing_requirements=["regime_runtime_labels_not_built"]`.
- The pipeline could fail at `model_quality_validation` with `'NoneType' object is not iterable`.
- A finished candidate could still surface as `candidate_status=UNKNOWN`.
- Critical gaps were not forced into an explicit gap gate failure path.
- Mandatory diagnostics propagation was incomplete in candidate summary payloads.

## Files Changed

- `app/training/training_pipeline_runner.py`
- `app/evaluation/model_quality_validator.py`
- `app/labels/regime_label_builder.py`
- `app/labels/regime_label_integration_status.py`
- `app/experiments/label_grid_experiment_runner.py`
- `app/experiments/feature_regime_experiment_runner.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/cli/commands.py`

## Runtime Regime Labels

- `regime_runtime_labels_not_built` is no longer hidden behind a silent fallback to base labels inside the real training runtime.
- The runtime label stage now reports explicit `built` or `blocked` status through `regime_label_builder_status`.
- When runtime regime labels cannot be built, the stage no longer continues as if the regime-aware path succeeded.

## NoneType Fix

- `model_quality_validation` now normalizes missing dict and list inputs before iterating.
- Missing diagnostics are converted into explicit warnings and blocked regime status instead of a Python exception.
- `candidate_selection` payload lists such as warnings, recommendations, failed_gates and passed_gates are normalized before propagation.

## Candidate Status Semantics

- Final completed candidates are normalized to `ACCEPTED` or `REJECTED`.
- Technical pipeline failures are normalized to `FAILED`.
- Final `candidate_status=UNKNOWN` is removed from the ML36.1 feature-regime and label-grid summaries.
- `evaluated_candidate_count` and `failed_candidate_count` are added so counts are consistent.

## Gap Gate

- The gap gate is explicitly forced into `failed_gates` when `gap_severity_for_training=CRITICAL`.
- `gap gate` failure now overrides a stale accepted selector payload and turns the final candidate into `REJECTED`.
- Critical gaps are visible in the final candidate and aggregate reports.

## Diagnostics Propagation

- Candidate summary propagation now includes `probability_diagnostics`.
- Candidate summary propagation now includes `collapse_diagnostics_v2`.
- Candidate summary propagation now includes `walk_forward_profit_diagnostics`.
- Candidate summary propagation now includes `profit_aware_diagnostics`.
- Candidate summary propagation now includes `regime_label_builder_status`.
- Feature-regime candidates now also carry `real_feature_diagnostics`.
- When a mandatory diagnostic is absent, the candidate summary carries an explicit missing reason instead of a silent empty dict.

## Safety

- traders-core integration: no
- live trading: no
- orders/trades: no
- model auto activation: no
- database migrations: no
- production deploy: no
