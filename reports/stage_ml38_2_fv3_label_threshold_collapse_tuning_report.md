# Stage ML38.2: FV3 Label, Threshold and Collapse Tuning

This report captures the completed ML38.2 implementation plus the fresh BTCUSDT/ETHUSDT/SOLUSDT FV3 tuning batch and final multi-symbol archive assembly.

## Run metadata

- branch: `ml38-2-fv3-label-threshold-collapse-tuning`
- commit hash: `c99d805`
- pytest result: `429 passed in 48.75s`
- CLI checks: `health`, `db-check`, `collapse-diagnostics-preview`, `regime-label-builder-preview`, `walk-forward-profit-diagnostics-preview`, `candle-ta-context-preview` for BTCUSDT/ETHUSDT/SOLUSDT, `ml38-2-fv3-tuning-preview`, `ml38-2-fv3-tuning-run`, and `multi-symbol-feature-regime-analyze --experiments-root reports/feature_regime_experiments --symbols BTCUSDT,ETHUSDT,SOLUSDT --latest-per-symbol` passed
- py_compile result: passed for `app/cli/commands.py`, `app/diagnostics/class_bias_diagnostics.py`, `app/diagnostics/collapse_tuning_summary.py`, `app/experiments/feature_regime_experiment_runner.py`, `app/experiments/multi_symbol_feature_regime_analyzer.py`, `app/experiments/multi_symbol_feature_regime_reporter.py`, `app/experiments/ml38_2_config_ranker.py`, `app/experiments/ml38_2_fv3_tuning_matrix.py`, `app/labels/label_quality_grid.py`
- fresh grid script path: `D:\disk_E\game_projects\traders\run_ml38_2_fv3_tuning_btc_eth_sol.ps1`
- fresh archive path: `D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments\ml38_2_fv3_tuning_3_symbols_15m_20260614_231852.zip`
- archive manifest: `reports/feature_regime_experiments/ml38_2_fv3_tuning_3_symbols_15m_20260614_231852/archive_manifest.json`
- archive size: `13.02 MB`
- archive note: symbol runs completed under the fresh-grid wrapper, but final orchestration stopped before archive creation; the archive was assembled manually from completed run artifacts without rerunning training

## Evaluation scope

- symbols evaluated: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`
- feature_version_used: `fv3_candle_ta_context` for all three symbols
- configs evaluated: `8 per symbol`, `24 total`
- accepted_candidate_count: `0`
- rejected_candidate_count: `24`
- best_config_by_symbol:
  - `BTCUSDT`: `lv2_h08_thr05_tp15_sl10`
  - `ETHUSDT`: `lv2_h08_thr03_tp10_sl10`
  - `SOLUSDT`: `lv2_h08_thr05_tp15_sl10`
- best_global_config: `lv2_h08_thr05_tp15_sl10`
- best_symbol: `BTCUSDT`
- best_candidate_score: `-2.0`

## Integration and safety checks

- real_feature_diagnostics_used: `true` for all symbols
- regime_features_attached: `true` for all symbols
- candle_ta_context_features_attached: `true` for all symbols
- gap_quality_gate: passed at multi-symbol level
- gap_severity_for_training: `OK` for all symbols
- orders/trades: disabled
- traders-core integration: disabled
- live trading: disabled
- model auto activation: disabled
- db migrations: none
- production deploy: none

## Collapse summary

- `collapse_gate` failed for all three symbols
- collapse types by best candidate:
  - `BTCUSDT`: `mixed`
  - `ETHUSDT`: `confidence_collapse`
  - `SOLUSDT`: `flat_bias`
- all three best candidates remained low-confidence with zero rows above `0.45` confidence and zero rows above `0.50`

## Flat bias summary

- `BTCUSDT`: `flat_bias_detected=true`, severity `CRITICAL`
- `ETHUSDT`: `flat_bias_detected=false`, severity `OK`
- `SOLUSDT`: `flat_bias_detected=true`, severity `HIGH`

## Down blindness summary

- `BTCUSDT`: `down_blindness_detected=true`
- `ETHUSDT`: `down_blindness_detected=false`
- `SOLUSDT`: `down_blindness_detected=false`

## Walk-forward summary

- walk-forward failed count: `2 of 3`
- `BTCUSDT`: `walk_forward_gate` passed, `WF PF=1.0374930558605095`, `WF R=76.96478511999912`
- `ETHUSDT`: `walk_forward_gate` failed, `WF PF=0.9179356827035852`, `WF R=-228.42923727000152`
- `SOLUSDT`: `walk_forward_gate` failed, `WF PF=0.9490903561455174`, `WF R=-89.72794622000049`

## Profit-aware summary

- profit-aware failed count: `0 of 3`
- `BTCUSDT`: `profit_aware_gate` passed, `profit_factor=1.7007901557889167`
- `ETHUSDT`: `profit_aware_gate` passed, `profit_factor=inf`
- `SOLUSDT`: `profit_aware_gate` passed, `profit_factor=1.081007505799397`

## Baseline-edge summary

- `BTCUSDT`: baseline accuracy edge `-0.01950448075909328`, `baseline_edge_gate` failed
- `ETHUSDT`: baseline accuracy edge `+0.015949632738719854`, `baseline_edge_gate` passed
- `SOLUSDT`: baseline accuracy edge `+0.000959488272921083`, but the edge was too small to rescue the candidate from collapse and walk-forward failures
- positive baseline edge symbols: `ETHUSDT`, `SOLUSDT`

## Why no model was accepted

- `BTCUSDT` remained the least-bad symbol, but its best candidate still failed `baseline_edge_gate`, `collapse_gate`, and `gap_quality_gate`, with both `flat_bias_detected` and `down_blindness_detected`.
- `ETHUSDT` removed the directional bias problem, but still collapsed on confidence and failed `walk_forward_gate`, so the positive baseline edge did not translate into robust out-of-sample behavior.
- `SOLUSDT` showed only a marginal positive baseline edge and still failed `baseline_edge_gate`, `collapse_gate`, `gap_quality_gate`, and `walk_forward_gate` because the model stayed FLAT-biased.
- At the portfolio level, `accepted_candidate_count=0`, `top_failed_gate=collapse_gate`, and multi-symbol robustness was not achieved.

## Final decision

- ML38.2 objective status: implementation complete, fresh batch complete, archive complete
- model acceptance decision: reject all candidates
- Can proceed to ML38.3: `yes`
- Can proceed to ML39: `no`

## Compatibility Notes

- flat bias: still present in BTCUSDT and SOLUSDT best candidates
- down blindness: still present in BTCUSDT best candidate
- collapse summary: all three best candidates still fail collapse evaluation
- traders-core integration: no
- live trading: no
- orders/trades: no
- model auto activation: no

| symbol | best_config | status | failed_gates | passed_gates | collapse_type | flat_bias_detected | down_blindness_detected | WF PF | WF R | accuracy | baseline | score |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSDT | lv2_h08_thr05_tp15_sl10 | REJECTED | baseline_edge_gate, collapse_gate, gap_quality_gate | gate_policy_replay_gate, profit_aware_gate, walk_forward_gate | mixed | 1 | 1 | 1.0374930558605095 | 76.96478511999912 | 0.33168160253031104 | 0.3511860832894043 | -2.0 |
| ETHUSDT | lv2_h08_thr03_tp10_sl10 | REJECTED | collapse_gate, walk_forward_gate | baseline_edge_gate, gap_quality_gate, gate_policy_replay_gate, profit_aware_gate | confidence_collapse | 0 | 0 | 0.9179356827035852 | -228.42923727000152 | 0.35498426023084995 | 0.3390346274921301 | -3.5 |
| SOLUSDT | lv2_h08_thr05_tp15_sl10 | REJECTED | baseline_edge_gate, collapse_gate, gap_quality_gate, walk_forward_gate | gate_policy_replay_gate, profit_aware_gate | flat_bias | 1 | 0 | 0.9490903561455174 | -89.72794622000049 | 0.3374200426439232 | 0.33646055437100214 | -7.5 |
