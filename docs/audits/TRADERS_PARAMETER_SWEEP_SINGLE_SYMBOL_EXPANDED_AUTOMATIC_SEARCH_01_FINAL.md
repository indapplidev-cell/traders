# TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_EXPANDED_AUTOMATIC_SEARCH_01 — FINAL

```text
FINAL_STATUS = PASS
FINAL_VERDICT = PASS_DESCRIPTIVE_ONLY_LOW_SAMPLE_EXPANDED_SEARCH_NOT_CERTIFIED

SYMBOL = DOGEUSDT
PROFILE = trade-5m-v2
SEARCH_SOURCE = DATA_DRIVEN_RANGE_HANDOFF

SOURCE_HISTORY_START = 2026-09-02T21:35:00+00:00
SOURCE_HISTORY_END = 2026-09-12T10:45:00+00:00
SOURCE_HISTORY_ACTUAL_DAYS = 9.54861111111111

ACTIVE_DIMENSION_COUNT = 4
ACTIVE_PARAMETERS = min_net_edge_bps; minimum_planned_rr; stop_max_bps; target_min_bps

RAW_CARTESIAN_COUNT = 1764
NORMALIZED_CARTESIAN_COUNT = 1764
PLANNED_CONFIGS = 500
EVALUATED_CONFIGS = 500

NUMERICALLY_DISTINCT_CONFIGS = 500
BEHAVIORALLY_DISTINCT_CONFIGS = 21
BEHAVIORAL_DUPLICATE_CONFIGS = 479

BEST_OBSERVED_CONFIG = {min_net_edge_bps: 1.0, minimum_planned_rr: 0.6, stop_max_bps: 50.0, target_min_bps: 60.0}
BEST_VALIDATION_TRADES = 3
BEST_WINS = 1
BEST_LOSSES = 2
BEST_NET_PNL = -0.04961941999999997 USDT
BEST_EXPECTANCY_R = NOT_AVAILABLE_IN_ACCEPTED_PERSISTED_SOURCE_NO_SUBSTITUTE_FORMULA_CREATED
BEST_PROFIT_FACTOR = 0.9535167395746674
BEST_MAX_DRAWDOWN = 1.06746858 USDT
BEST_INDEPENDENT_PERIODS = 1

POSITIVE_OBSERVED_CONFIGS = 2
VALIDATION_ELIGIBLE_CONFIGS = 0

BEST_BOUNDARY_MIN_NET_EDGE_BPS = AT_LOW_BOUNDARY
BEST_BOUNDARY_MINIMUM_PLANNED_RR = AT_LOW_BOUNDARY
BEST_BOUNDARY_STOP_MAX_BPS = AT_HIGH_BOUNDARY
BEST_BOUNDARY_TARGET_MIN_BPS = INTERIOR

SEARCH_VALUE_NORMALIZATION_CREATED = YES
EXPANDED_SEARCH_HANDOFF_CREATED = YES
LEGACY_COMPARISON_CREATED = YES

SCHEMA_VIOLATIONS = 0
HANDOFF_FALLBACKS_TO_LEGACY = 0
NEW_VALUES_CREATED_DURING_SEARCH = 0
RECONSTRUCTED_ROWS_USED = 0
CROSS_SYMBOL_ROWS = 0

SEARCH_SPACE_FROZEN = YES_BEFORE_FIRST_EVALUATION
BYTE_DETERMINISM = PASS_ALL_ARTIFACT_SHA256_UNCHANGED_AFTER_RESUME
RESUME_GUARDS = PASS_SYMBOL_PROFILE_DATASET_HANDOFF_SEARCHSPACE_SEED_FAIL_CLOSED

PROMOTION_ELIGIBLE = NO
ADAPTIVE_REFINEMENT_EXECUTED = NO
HOLDOUT_OPENED = NO

TESTS = PASS_209_RESEARCH_TESTS; PASS_29_FOCUSED_AND_RANGE_REGRESSION_TESTS
COMPILE = PASS_PYTHON_COMPILEALL

FILES_CHANGED = traders_ml/parameter_sweep/expanded_search.py; traders_ml/parameter_sweep/data_driven_ranges.py; tests/research/test_parameter_sweep_expanded_search.py; docs/audits/TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_EXPANDED_AUTOMATIC_SEARCH_01_FINAL.md; online_trader.md; ignored research artifacts under artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01 and upgraded ignored DATA_DRIVEN_RANGE_HANDOFF.json
COMMITS = PROJECT_STATE_d730dcb4df0a08105253eadd74b8d93d55e902da; DOCUMENTATION_RECONCILIATION_RESOLVE_WITH_GIT_LOG_ON_THIS_FILE
PUSH = NOT_PERFORMED
AHEAD_BEHIND = LOCAL_AHEAD2_BEHIND0_AT_FINAL_VERIFICATION
WORKTREE = CLEAN_AT_FINAL_VERIFICATION

PRODUCTION_TRADING_LOGIC_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
VALIDATION_GATES_20_3_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO

LIVE_STATE = DISABLED_FALSE
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

OUT_OF_SCOPE_ISSUES = AUTHORITATIVE_EXPECTANCY_R_NORMALIZER_ABSENT_FROM_ACCEPTED_10_TRADE_PERSISTED_SEPARABILITY_DATASET; REPORTED_NULL_WITHOUT_INVENTING_A_FORMULA
REMAINING_BLOCKERS = VALIDATION_SAMPLE_3_TRADES_AND_1_INDEPENDENT_UTC_PERIOD_FOR_BEST_RESULT_BELOW_CANONICAL_20_AND_3; SOURCE_SAMPLE_REMAINS_DESCRIPTIVE_ONLY
NEXT_RECOMMENDED_ACTION = SEPARATE_ADAPTIVE_REFINEMENT_TASK_MAY_CONSUME_EXPANDED_SEARCH_HANDOFF_JSON_WITHOUT_NEW_VALUES_UNTIL_EXPLICITLY_AUTHORIZED
```

## Search and provenance

The active domains were read from the v2 `DATA_DRIVEN_RANGE_HANDOFF` contract.
The contract migration added symbol, profile, sample adequacy, typed schema,
eligibility and provenance to the already generated v1 values; it did not
recalculate, round, expand or otherwise change any candidate value. Parameters
without an eligible `GENERATED` or `PROVISIONAL_LOW_SAMPLE` row are absent from
the search. Legacy arrays are loaded only by the paired benchmark after the
data-driven campaign has been frozen.

All four consumers use direct inclusive numeric threshold comparisons. Their
effective numeric precision is the consumed IEEE-754 binary64 value and their
serialization is shortest-round-trip JSON. Therefore the only allowed
normalization is exact consumed-value identity; no arbitrary decimal rounding
was applied and the current DOGE domains lost zero values.

The accepted source is the same immutable ten-trade, exact pre-entry persisted
causal dataset used by the separability handoff. The broader persisted source
inventory spans 9.548611 days and 2,685 observations. The search uses a frozen
chronological 60/40 calibration/validation split and never constructs or reads
a holdout split. Fixed parameters retain the current authoritative
`trade-5m-v2` values.

## Ranking and behavioral accounting

The run uses the existing `rank_results` semantics and the existing artifact-v2
validation trade signature. Behavioral cluster identity adds the existing
validation outcome and funnel signatures, so aliases with identical admitted
trades, outcomes and rejection funnel contribute one ranked representative.
All 500 raw evaluated rows remain in `EXPANDED_SEARCH_RESULTS.jsonl`; the 479
aliases are traceable in `BEHAVIORAL_CLUSTERS.json`.

The accepted source does not contain an authoritative realized-risk denominator.
Consequently `expectancy_R` is null. Using net USDT PnL as R or inventing a new
normalizer would have changed canonical profitability semantics and was not
done. The result remains useful only as observed descriptive evidence.

## Paired legacy comparison

```text
LEGACY_COMPARISON_STATUS = PAIRED_SAME_FROZEN_DATASET_DIAGNOSTIC_ONLY
LEGACY_RAW_CONFIGS = 144
LEGACY_EVALUATED_CONFIGS = 144
LEGACY_BEHAVIORALLY_DISTINCT_CONFIGS = 2
LEGACY_BEST_VALIDATION_TRADES = 3
LEGACY_BEST_NET_PNL = -0.04961941999999997 USDT
LEGACY_BEST_EXPECTANCY_R = NOT_AVAILABLE
LEGACY_BEST_PROFIT_FACTOR = 0.9535167395746674
LEGACY_POSITIVE_OBSERVED_CONFIGS = 0

DATA_DRIVEN_RAW_CONFIGS = 1764
DATA_DRIVEN_EVALUATED_CONFIGS = 500
DATA_DRIVEN_BEHAVIORALLY_DISTINCT_CONFIGS = 21
DATA_DRIVEN_BEST_VALIDATION_TRADES = 3
DATA_DRIVEN_BEST_NET_PNL = -0.04961941999999997 USDT
DATA_DRIVEN_BEST_EXPECTANCY_R = NOT_AVAILABLE
DATA_DRIVEN_BEST_PROFIT_FACTOR = 0.9535167395746674
DATA_DRIVEN_POSITIVE_OBSERVED_CONFIGS = 2

CAUSAL_IMPROVEMENT_CLAIM = NOT_AUTHORIZED
```

The legacy run is a small exhaustive benchmark on the exact same frozen
dataset. It is not a fallback source and cannot fill a missing data-driven
dimension.

## Artifacts

```text
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/EXPANDED_SEARCH_CONFIG.json
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/SEARCH_VALUE_NORMALIZATION.json
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/EXPANDED_SEARCH_RESULTS.jsonl
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/BEHAVIORAL_CLUSTERS.json
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/LEGACY_EXPANDED_SEARCH_COMPARISON.json
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/EXPANDED_SEARCH_HANDOFF.json
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/REPORT.md
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/STATUS.json
```
