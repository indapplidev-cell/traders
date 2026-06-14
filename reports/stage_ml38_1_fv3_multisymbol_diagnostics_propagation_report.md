# Stage ML38.1: FV3 Multisymbol Diagnostics Propagation

## Scope

Stage ML38.1 fixes the ML38 regression where `fv3_candle_ta_context` was attached for BTCUSDT but lost for ETHUSDT and SOLUSDT in multi-symbol propagation. The goal is to make `candle_ta_context_features_attached`, `real_feature_diagnostics_used`, and `regime_features_attached` propagate consistently for all three symbols and to prevent any silent fallback.

## What was broken

- ML38 produced a useful BTCUSDT result, but ETHUSDT and SOLUSDT could finish with missing `fv3_candle_ta_context` attachment.
- The main failure mode was multi-symbol propagation and diagnostics propagation, not the candle feature logic itself.
- The runner could rely on stale or absent persisted feature rows before the real pipeline built current rows.
- That created a silent fallback path where `false` values could appear without a strong explicit missing reason.

## Fix direction

- Prefer runtime feature construction for `fv3_candle_ta_context` when persisted rows are missing or partial.
- Preserve explicit missing reasons for `candle_ta_context_features_attached`, `real_feature_diagnostics_used`, and `regime_features_attached`.
- Keep candidate summaries and aggregate multi-symbol summaries aligned.
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

## Tests added

- `tests/test_ml38_1_fv3_multisymbol_attachment.py`
- `tests/test_ml38_1_real_diagnostics_propagation.py`
- `tests/test_ml38_1_no_silent_fv3_fallback.py`
- `tests/test_ml38_1_multisymbol_report_fields.py`
- `tests/test_stage_ml38_1_report.py`

## Expected runtime fields

- `feature_version=fv3_candle_ta_context`
- `candle_ta_context_features_attached=true`
- `real_feature_diagnostics_used=true`
- `regime_features_attached=true`
- explicit missing reason fields when attachment fails

## Checks

`pytest results`: pending final full run after ML38.1 code changes.  
`CLI results`: pending final full run after ML38.1 code changes.

## Fresh BTC/ETH/SOL grid

Pending final ML38.1 fresh run for BTCUSDT, ETHUSDT, and SOLUSDT. The final report update must record the fresh archive path, final per-symbol table, and aggregate decision fields.

## Decision

`Can proceed to ML38.2 tuning`: pending fresh validation.  
`Can proceed to ML39 Schwager evaluation hardening`: pending fresh validation.

## Safety

- no traders-core
- no live
- no orders
- no auto activation
- no db migrations
- no production deploy
