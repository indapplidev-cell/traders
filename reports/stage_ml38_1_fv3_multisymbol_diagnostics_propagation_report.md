# Stage ML38.1: FV3 Multisymbol Diagnostics Propagation

## Scope

Stage ML38.1 fixes the ML38 regression where `fv3_candle_ta_context` was already attached inside the candle preview path for BTCUSDT, ETHUSDT, and SOLUSDT, but the experiment diagnostics path could still report missing attachment for ETHUSDT and SOLUSDT during multi-symbol propagation. The goal was to make `candle_ta_context_features_attached`, `real_feature_diagnostics_used`, and `regime_features_attached` propagate consistently for all three symbols and to prevent any silent fallback.

## What was broken

- The main failure mode was multi-symbol propagation and diagnostics propagation, not the candle feature logic itself.
- BTCUSDT could appear healthy because persisted fv3 rows already existed, so diagnostics picked up attached rows from storage.
- ETHUSDT and SOLUSDT could appear unattached because diagnostics ran before current runtime fv3 rows were built and could fall back to stale or missing persisted rows.
- That created a silent fallback path where `false` values could appear without a strong explicit missing reason even though the runtime builder was capable of producing valid fv3 rows.

## Fix direction

- Prefer runtime feature construction for `fv3_candle_ta_context` when persisted rows are missing or partial.
- Preserve explicit missing reasons for `candle_ta_context_features_attached`, `real_feature_diagnostics_used`, and `regime_features_attached`.
- Keep candidate summaries and aggregate multi-symbol summaries aligned.
- Reject stale or partial dataset rows for requested fv3 instead of silently counting them as success.
- Keep `candidate_status` honest and avoid `UNKNOWN` for ordinary quality rejection.

## Files changed

- `app/diagnostics/real_feature_diagnostics_service.py`
- `app/experiments/feature_regime_experiment_runner.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/cli/commands.py`
- `tests/test_ml36_1_candidate_diagnostics_propagation.py`
- `tests/test_ml38_1_fv3_multisymbol_attachment.py`
- `tests/test_ml38_1_real_diagnostics_propagation.py`
- `tests/test_ml38_1_no_silent_fv3_fallback.py`
- `tests/test_ml38_1_multisymbol_report_fields.py`
- `tests/test_stage_ml38_1_report.py`

## Implementation summary

- `real_feature_diagnostics_service` now reports explicit fv3 attachment counts and missing reasons, including `candle_ta_context_feature_count`, `regime_feature_count`, and `candle_ta_context_missing_reason`.
- `feature_regime_experiment_runner` now builds runtime diagnostic rows with `FeatureBuilder` when persisted rows do not satisfy `fv3_candle_ta_context`, propagates missing reasons, and prevents silent fallback to stale partial rows.
- `multi_symbol_feature_regime_analyzer` now preserves per-symbol attachment counts and missing reasons in aggregate output so multi-symbol propagation no longer drops ETHUSDT or SOLUSDT diagnostics.
- `multi_symbol_feature_regime_reporter` and CLI analysis output now expose those propagated fields in the final summary artifacts.

## Tests added

- `tests/test_ml38_1_fv3_multisymbol_attachment.py`
- `tests/test_ml38_1_real_diagnostics_propagation.py`
- `tests/test_ml38_1_no_silent_fv3_fallback.py`
- `tests/test_ml38_1_multisymbol_report_fields.py`
- `tests/test_stage_ml38_1_report.py`

## Diagnostics propagation details

- Multi-symbol propagation is now driven by the same final per-symbol diagnostics fields that the experiment runner computes after runtime fv3 row validation.
- diagnostics propagation now keeps `real_feature_diagnostics_missing_reason`, `regime_features_missing_reason`, `candle_ta_context_feature_count`, `candle_ta_context_missing_reason`, and `regime_feature_count` for every symbol.
- silent fallback is blocked by validating requested feature attachment before dataset rows can satisfy diagnostics for `fv3_candle_ta_context`.

## Checks

`pytest results`: `420 passed in 46.90s`  
`CLI results`: `health`, `db-check`, `collapse-diagnostics-preview`, `regime-label-builder-preview`, `walk-forward-profit-diagnostics-preview`, and `candle-ta-context-preview` for BTCUSDT, ETHUSDT, SOLUSDT all passed.  
`py_compile results`: passed for feature builder, diagnostics, experiment runner, analyzer, reporter, and CLI modules.

## Fresh BTC/ETH/SOL grid

- fresh archive: `reports\feature_regime_experiments\ml38_1_candle_ta_3_symbols_15m_20260614_190258.zip`
- Fresh run completed successfully with exit code `0`.
- Aggregate summary:
- `all_feature_version_fv3_candle_ta_context=true`
- `all_real_feature_diagnostics_used=true`
- `symbols_missing_real_diagnostics=[]`
- `symbols_missing_regime_features=[]`
- `symbols_missing_candle_ta_context_features=[]`
- `all_gap_training_safe=true`
- `accepted_candidate_count=0`
- `best_symbol=BTCUSDT`
- `best_candidate_score=-7.992515`
- `gate_failure_counts={baseline_edge_gate: 3, collapse_gate: 3, profit_aware_gate: 2, walk_forward_gate: 2}`

## Symbol results

| symbol | feature_version | candidate_status | failed_gates | passed_gates | regime_label_builder_used_in_training | regime_specific_training_applied | candle_ta_context_features_attached | candle_ta_context_feature_count | real_feature_diagnostics_used | real_feature_diagnostics_row_count | regime_features_attached | regime_feature_count | model_quality_validation_status | collapse_detected | walk_forward_profit_factor | walk_forward_total_r | accuracy | best_baseline_accuracy | predicted_class_distribution | actual_class_distribution |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| BTCUSDT | fv3_candle_ta_context | REJECTED | baseline_edge_gate, collapse_gate, profit_aware_gate | gap_quality_gate, gate_policy_replay_gate, walk_forward_gate | true | true | true | 170 | true | 47027 | true | 8 | COMPLETED | true | 1.050267 | 130.002050 | 0.315472 | 0.371697 | DOWN 0.093743, FLAT 0.525365, UP 0.380892 | DOWN 0.393786, FLAT 0.234517, UP 0.371697 |
| ETHUSDT | fv3_candle_ta_context | REJECTED | baseline_edge_gate, collapse_gate, profit_aware_gate, walk_forward_gate | gap_quality_gate, gate_policy_replay_gate | true | true | true | 170 | true | 48092 | true | 8 | COMPLETED | true | 0.938335 | -171.081187 | 0.352187 | 0.361123 | DOWN 0.284272, FLAT 0.419891, UP 0.295837 | DOWN 0.380046, FLAT 0.258831, UP 0.361123 |
| SOLUSDT | fv3_candle_ta_context | REJECTED | baseline_edge_gate, collapse_gate, walk_forward_gate | gap_quality_gate, gate_policy_replay_gate, profit_aware_gate | true | true | true | 170 | true | 47786 | true | 8 | COMPLETED | true | 0.935167 | -143.223691 | 0.314389 | 0.355197 | DOWN 0.034398, FLAT 0.596197, UP 0.369405 | DOWN 0.391945, FLAT 0.252858, UP 0.355197 |

## Decision

`Can proceed to ML38.2 tuning`: yes  
`Can proceed to ML39 Schwager evaluation hardening`: no

Rationale:
ML38.1 succeeded because fv3 attachment and diagnostics propagation now hold for BTCUSDT, ETHUSDT, and SOLUSDT with real runtime rows and no missing symbols. ML39 should not start yet because all three candidates remain rejected and collapse remains unresolved across the full batch.

## Safety

- no traders-core
- no live
- no orders
- no auto activation
- no db migrations
- no production deploy
