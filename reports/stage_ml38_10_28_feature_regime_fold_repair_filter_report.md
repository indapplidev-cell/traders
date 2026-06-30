# ML38.10.28 Feature/Regime Fold Repair Filter Report

## Scope

ML38.10.28 does not accept a model for live use. The stage replaces the research-only `bad-date blackout` idea with a research-only `feature/regime fold repair filter` probe and keeps `lv31` as the date-blackout baseline.

## Added lv32 configs

- `lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe`
- `lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe`
- `lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe`
- `lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe`
- `lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_feature_guard_probe`
- `lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_strict_feature_guard_exit45_probe`

## Baseline and safety

- `lv31` date-blackout configs were kept unchanged as the research baseline.
- All `lv32` configs are research-only and acceptance-blocked.
- `lv32` uses `fold_repair_feature_filter_enabled=True`.
- `lv32` does not use `fold_repair_blackout_dates` for filtering.
- `accepted_candidate_count` remains `0`.

## Validation

- `python -m py_compile app/labels/label_quality_grid.py app/evaluation/profit_aware_evaluator_v2.py app/experiments/feature_regime_experiment_runner.py app/experiments/label_grid_experiment_runner.py app/experiments/ml38_2_fv3_tuning_matrix.py app/experiments/multi_symbol_feature_regime_analyzer.py app/experiments/multi_symbol_feature_regime_reporter.py app/experiments/feature_regime_experiment_reporter.py app/diagnostics/fold_feature_regime_repair_probe.py run_fv3_cached_tuning.py`
- `python -m pytest -q tests/test_ml38_10_28_feature_regime_fold_repair_filter.py tests/test_ml38_10_27_1_runtime_shortlist_config_registration.py tests/test_ml38_10_27_fold_time_slice_exit_repair_probe.py`
  Result: `14 passed`
- `python -m pytest -q`
  Result: `771 passed`

## Runtime commands executed

- `python clean_traders_ml.py --cleanup-commit-only`
- `python run_fv3_cached_tuning.py --fast-debug`
- `python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT`

## Runtime archives

- Fast debug archive:
  `D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments\fast_debug_fv3_cached_fresh_tuning_btcusdt_solusdt_15m_20260629_191259.zip`
- Quick quality archive:
  `D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260629_203621.zip`

## Final runtime summary

- Fast debug:
  `expected_candidate_count=28`, `candidate_count=28`, `failed_candidate_count=0`, `accepted_candidate_count=0`
- Quick quality SOLUSDT:
  `expected_candidate_count=30`, `candidate_count=30`, `failed_candidate_count=0`, `accepted_candidate_count=0`

## Best-candidate comparison

- Best `lv32` quick-quality probe:
  `lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_strict_feature_guard_exit45_probe`
  `PF=1.3650851115857277`, `Total R=8.240545846401288`, `WF PF=0.0`, `WF Total R=0.0`
- Best `lv31` date-blackout baseline:
  `lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe`
  `PF=1.4073880546739959`, `Total R=9.810545846401292`, `WF PF=1.0716948164711737`, `WF Total R=2.730403177759829`
- `fold_feature_regime_repair_probe` verdict:
  `FEATURE_REGIME_FILTER_NOT_YET_A_REPLACEMENT`

## Conclusion

ML38.10.28 is technically complete and remains research-only. The feature/regime filter produced viable `lv32` candidates, but it did not yet replace the `lv31` date-blackout baseline out of sample, so the model must remain blocked from acceptance.
