# ML38.10.27.1 - Runtime shortlist config registration fix

## Problem

`run_fv3_cached_tuning.py --fast-debug` failed before training because the wrapper passed lv31 config ids that were present in runtime shortlists but absent from `ML38_2_FV3_TUNING_CONFIG_IDS`.

Missing ids observed:

- `lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe`
- `lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe`

## Fix

- Added `ML38_10_27_FOLD_TIME_SLICE_EXIT_REPAIR_CONFIG_IDS` to `app/experiments/ml38_2_fv3_tuning_matrix.py`.
- Included the ML38.10.27 group in `ML38_2_FV3_TUNING_CONFIG_IDS`.
- Added matrix metadata for the fold time-slice / exit repair probe group.
- Added wrapper preflight validation to fail early if selected runtime configs are not registered.
- Added regression tests that verify all fast-debug and quick-quality runtime configs exist in both `LabelQualityGridPlanner` and `ML382FV3TuningMatrix`.

## Runtime counts

- `--fast-debug`: 24 expected candidates.
- `--quick-quality --quick-quality-symbol SOLUSDT`: 26 expected candidates.

## Safety

ML38.10.27 lv31 probes remain research-only and must not become accepted/live candidates.
