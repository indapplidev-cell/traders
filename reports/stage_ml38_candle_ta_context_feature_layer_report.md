# Stage ML38: Candle TA Context Feature Layer

## Goal

ML38 introduced `fv3_candle_ta_context` as a new feature layer for feature-regime experiments. The goal was to formalize candle and technical context ideas into numeric features and diagnostics, keep old feature versions backward compatible, protect against lookahead leakage, and run a fresh BTCUSDT/ETHUSDT/SOLUSDT grid without any runtime crash.

## Formalized sources

- Nison: candle morphology, doji/hammer/shooting star style scoring, engulfing logic, star-pattern soft scoring, windows/gaps, context-aware pattern validation.
- Altunina: trend slope/strength/age, impulse/correction structure, support/resistance distances and touches, Bollinger, MACD, RSI, Stochastic, Momentum, ROC, and volume-context adaptation.

## Added feature groups

- candle morphology
- candle patterns
- technical context
- trend_context
- support_resistance
- indicators
- volume_context

Key features included `candle_range`, `body_to_range_ratio`, `shadow_imbalance`, `doji_score`, `hammer_score`, `bullish_engulfing_score`, `trend_slope_short`, `trend_strength_medium`, `distance_to_support`, `distance_to_resistance`, `bollinger_position`, `macd_histogram`, `stochastic_k`, `roc`, `momentum`, and `volume_zscore`.

## Safety and correctness

`lookahead` protection was implemented by building every feature row from candles at time `<= T` only. A dedicated leakage test mutates a future candle and verifies that prior rows stay unchanged. `NaN/inf` safety was enforced through safe division, bounded ratios, and stable defaults for short-history windows; the fv3 preview produced `nan_feature_count=0` and `inf_feature_count=0`.

Safety constraints remained unchanged: no traders-core, no live, no orders, no auto activation, no migrations, no production deploy, and no move to ML39 inside implementation scope.

## files changed

- `app/features/__init__.py`
- `app/features/feature_builder.py`
- `app/features/feature_models.py`
- `app/features/technical_indicators.py`
- `app/diagnostics/feature_group_quality.py`
- `app/diagnostics/real_feature_diagnostics_service.py`
- `app/experiments/feature_regime_experiment_runner.py`
- `app/experiments/label_grid_experiment_runner.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/cli/commands.py`
- `reports/stage_ml38_candle_ta_context_feature_layer_report.md`

External ML38 runner script created outside git history:

- `D:\disk_E\game_projects\traders\run_ml38_candle_ta_context_btc_eth_sol.ps1`

## tests added

- `tests/test_ml38_candle_morphology_features.py`
- `tests/test_ml38_candle_pattern_scores.py`
- `tests/test_ml38_technical_context_features.py`
- `tests/test_ml38_feature_version_fv3_integration.py`
- `tests/test_ml38_no_lookahead_leakage.py`
- `tests/test_ml38_nan_inf_safety.py`
- `tests/test_ml38_feature_regime_summary.py`
- `tests/test_stage_ml38_report.py`

## pytest results

`python -m pytest` completed successfully: `415 passed in 50.82s`.

## CLI results

- `python -m app.cli.commands health`: passed
- `python -m app.cli.commands db-check`: passed
- `python -m app.cli.commands collapse-diagnostics-preview`: passed
- `python -m app.cli.commands regime-label-builder-preview`: passed
- `python -m app.cli.commands walk-forward-profit-diagnostics-preview`: passed
- `python -m app.cli.commands candle-ta-context-preview --symbol BTCUSDT --interval 15m --limit 300`: passed, `feature_version=fv3_candle_ta_context`, `candle_ta_context_features_attached=true`, `regime_features_attached=true`, `real_feature_diagnostics_used=true`, no NaN/inf
- `python -m py_compile ...`: passed for all changed runtime files

## Fresh grid

Branch: `ml38-candle-ta-context-feature-layer`  
Commit: `11d7ded Add ML38 candle TA context feature layer`  
`git status --short` after commit: clean  
Fresh grid status: completed without runtime failure, archive produced

Fresh archive produced during the ML38 run:

- `reports\feature_regime_experiments\ml38_candle_ta_3_symbols_15m_20260614_170740.zip`

| Symbol | feature_version | status | failed_gates | passed_gates | real_diag | regime_features | candle_ta | collapse | wf_pf | wf_total_r | acc | baseline_acc |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| BTCUSDT | `fv3_candle_ta_context` | `REJECTED` | `baseline_edge_gate, collapse_gate, profit_aware_gate` | `gap_quality_gate, gate_policy_replay_gate, walk_forward_gate` | true | true | true | true | 1.050267 | 130.002050 | 0.315706 | 0.371973 |
| ETHUSDT | `fv3_candle_ta_context` | `REJECTED` | `baseline_edge_gate, collapse_gate, profit_aware_gate, walk_forward_gate` | `gap_quality_gate, gate_policy_replay_gate` | false | false | false | true | 0.938335 | -171.081187 | 0.352310 | 0.361465 |
| SOLUSDT | `fv3_candle_ta_context` | `REJECTED` | `baseline_edge_gate, collapse_gate, walk_forward_gate` | `gap_quality_gate, gate_policy_replay_gate, profit_aware_gate` | false | false | false | true | 0.935167 | -143.223691 | 0.314585 | 0.355539 |

Detailed class distributions from the fresh grid:

- BTCUSDT predicted `{DOWN: 0.0938, FLAT: 0.5254, UP: 0.3808}` vs actual `{DOWN: 0.3933, FLAT: 0.2347, UP: 0.3720}`
- ETHUSDT predicted `{DOWN: 0.2844, FLAT: 0.4201, UP: 0.2955}` vs actual `{DOWN: 0.3798, FLAT: 0.2588, UP: 0.3615}`
- SOLUSDT predicted `{DOWN: 0.0344, FLAT: 0.5967, UP: 0.3689}` vs actual `{DOWN: 0.3917, FLAT: 0.2528, UP: 0.3555}`

Additional fresh-grid facts:

- `accepted_candidate_count=0`
- `all_feature_version_fv3_candle_ta_context=true`
- `best_symbol=BTCUSDT`
- `symbols_missing_real_diagnostics=[ETHUSDT, SOLUSDT]`
- `symbols_missing_regime_features=[ETHUSDT, SOLUSDT]`
- `symbols_missing_candle_ta_context_features=[ETHUSDT, SOLUSDT]`
- gap quality remained safe for BTCUSDT and critical for ETHUSDT/SOLUSDT

## Comparison vs ML36.2 fresh run

Baseline ML36.2 fresh result was: BTCUSDT rejected with WF PF about `0.9720` and total R about `-39.41R`; ETHUSDT rejected with WF PF about `0.9678` and total R about `-57.73R`; SOLUSDT rejected with WF PF about `0.8992` and total R about `-184.23R`.

ML38 comparison:

- BTCUSDT improved materially in walk-forward behavior, moving to `walk_forward_profit_factor=1.050267` and `walk_forward_total_r=130.002050`, but baseline edge became negative and `collapse_detected=true` remained.
- ETHUSDT worsened overall: walk-forward PF fell to `0.938335`, total R became more negative, and both real diagnostics and regime features were missing in the fresh result.
- SOLUSDT improved relative to ML36.2 in walk-forward PF and total R, and `profit_aware_gate` passed, but collapse still remained and real diagnostics/regime features were missing.
- Predicted distributions are still too far from actual distributions, especially BTCUSDT DOWN underprediction and SOLUSDT DOWN underprediction, so confidence separation did not become healthy enough.
- Result: collapse improved in a mixed way, not solved.

## Final conclusion

ML38 is technically completed: `yes`. The model accepted status is `no`; all three symbols finished as honest `REJECTED`, not runtime `FAILED`. The next recommended stage is an ML38.1-style persistence/diagnostics repair for ETHUSDT and SOLUSDT attachment loss before any ML39 work, followed by another fresh fv3 validation run.
