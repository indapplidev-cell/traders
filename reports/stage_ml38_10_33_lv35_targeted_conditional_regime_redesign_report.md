# ML38.10.33 — lv35 targeted conditional regime redesign

## Root cause

ML38.10.32 showed that the only active lv34 rule,
`high_volatility_low_entry_quality`, is unstable and harmful on SOLUSDT quick-quality.
It removed profitable signals and should not be strengthened.

## Changes

- Added metric_logic support for conditional regime rules:
  - any
  - all
  - min_count
- Added rule metadata to ablation board:
  - metric_logic
  - required_metric_failure_count
  - metric_condition_count
- Added lv35 targeted conditional regime-risk configs.
- lv35 uses stricter multi-metric rules.
- lv35 does not include standalone high_volatility_low_entry_quality.
- Registered lv35 in label grid, FV3 matrix, and runtime shortlists.
- Runtime commands were not executed in this stage.

## Safety

- No model activation.
- No live trading.
- lv35 is research-only.
- No cleanup command executed.
- No runtime command executed.

## Future runtime counts

- fast-debug = 40 candidates.
- quick-quality SOLUSDT = 42 candidates.

## Tests

- py_compile
- targeted pytest
- full pytest
