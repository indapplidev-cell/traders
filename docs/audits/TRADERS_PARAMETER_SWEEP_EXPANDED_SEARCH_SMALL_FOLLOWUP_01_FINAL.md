# TRADERS_PARAMETER_SWEEP_EXPANDED_SEARCH_SMALL_FOLLOWUP_01 — FINAL

```text
FINAL_STATUS = PASS
FINAL_VERDICT = PASS_REPORTING_DISAMBIGUATED_AND_UNIVERSAL_SYMBOL_ENGINE_PROVEN

SYMBOL = DOGEUSDT
PROFILE = trade-5m-v2

BEST_OBSERVED_SELECTION_BASIS = CANONICAL_RESEARCH_RANKING_EXPECTANCY_R_DESC_PROFIT_FACTOR_DESC_MAX_DRAWDOWN_ASC_CAPPED_TRADE_COUNT_DESC_SYMBOL_COVERAGE_DESC_RANK_STABILITY_DESC_CONFIG_ID_DESC

BEST_CANONICAL_RANKED_CONFIG = {min_net_edge_bps: 1.0, minimum_planned_rr: 0.6, stop_max_bps: 50.0, target_min_bps: 60.0}
BEST_CANONICAL_RANKED_NET_PNL = -0.04961941999999997 USDT
BEST_CANONICAL_RANKED_EXPECTANCY = NOT_AVAILABLE
BEST_CANONICAL_RANKED_PF = 0.9535167395746674

BEST_NET_PNL_CONFIG = {min_net_edge_bps: 73.004386, minimum_planned_rr: 1.953403, stop_max_bps: 48.496589, target_min_bps: 49.163216}
BEST_NET_PNL = 1.01784916 USDT

BEST_EXPECTANCY_CONFIG = NOT_AVAILABLE
BEST_EXPECTANCY = NOT_AVAILABLE

BEST_PROFIT_FACTOR_CONFIG = {min_net_edge_bps: 1.0, minimum_planned_rr: 0.6, stop_max_bps: 50.0, target_min_bps: 60.0}
BEST_PROFIT_FACTOR = 0.9535167395746674

POSITIVE_NUMERIC_CONFIGS = 108
POSITIVE_BEHAVIORAL_CLUSTERS = 2
POSITIVE_BEHAVIORAL_DUPLICATES = 106

RUNTIME_SYMBOL_HARDCODES = 0
RUNTIME_SYMBOL_DEFAULTS = 0
RUNTIME_SYMBOL_BRANCHES = 0

SYMBOL_AUTHORITY_SOURCE = app.trading_universe.domain:trading-universe-v2
GUI_SYMBOL_SOURCE = ParameterSweepWindow.symbol_selector_TO_ParameterSweepController.start_new_run_TO_validate_parameter_sweep_symbol
CLI_SYMBOL_SOURCE = PARAMETER_SWEEP_CLI_REQUIRED_SYMBOL_AND_EXPANDED_SEARCH_CLI_REQUIRED_SYMBOL_TO_validate_parameter_sweep_symbol
RUN_CONFIG_SYMBOL_SOURCE = VALIDATED_SELECTED_SYMBOL_PERSISTED_IN_EXPANDED_SEARCH_CONFIG_AND_CHECKPOINT

DATASET_SYMBOL_BINDING = EVERY_ROW_EQUALS_VALIDATED_SELECTED_SYMBOL_OR_FAIL_CLOSED
SEPARABILITY_SYMBOL_BINDING = EXPLICIT_REQUIRED_SYMBOL_QUERY_FILTER_AND_MANIFEST_PROPAGATION_NO_DEFAULT
RANGE_HANDOFF_SYMBOL_BINDING = COPIED_FROM_SEPARABILITY_MANIFEST_AND_EQUALITY_VALIDATED
EXPANDED_SEARCH_SYMBOL_BINDING = VALIDATED_AGAINST_TRADING_UNIVERSE_V2_BEFORE_HANDOFF_AND_DATASET
RESUME_SYMBOL_BINDING = CHECKPOINT_SYMBOL_EXACT_EQUALITY_OR_FAIL_CLOSED

DOGE_FIXTURE = PASS_SAME_ENGINE_CODE_PATH
LINK_FIXTURE = PASS_SAME_ENGINE_CODE_PATH
HANDOFF_SYMBOL_MISMATCH_TEST = PASS_FAIL_CLOSED_HANDOFF_SYMBOL_MISMATCH
DATASET_SYMBOL_MISMATCH_TEST = PASS_FAIL_CLOSED_CROSS_SYMBOL_CONTAMINATION
RESUME_SYMBOL_MISMATCH_TEST = PASS_FAIL_CLOSED_RESUME_SYMBOL_MISMATCH
MISSING_SYMBOL_FAIL_CLOSED_TEST = PASS_SYMBOL_REQUIRED_NO_FALLBACK

SEARCH_RANKING_CHANGED = NO
SEARCH_SPACE_CHANGED = NO
RANGES_CHANGED = NO
VALIDATION_20_3_CHANGED = NO

ADAPTIVE_REFINEMENT_EXECUTED = NO
HOLDOUT_OPENED = NO
PROMOTION_ELIGIBLE = NO

TESTS = PASS_214_RESEARCH_TESTS; PASS_17_FOCUSED_TESTS
COMPILE = PASS_PYTHON_COMPILEALL

FILES_CHANGED = traders_ml/parameter_sweep/expanded_search.py; traders_ml/parameter_sweep/separability.py; traders_ml/parameter_sweep/symbol_authority_audit.py; tests/research/test_parameter_sweep_expanded_search.py; docs/audits/TRADERS_PARAMETER_SWEEP_EXPANDED_SEARCH_SMALL_FOLLOWUP_01_FINAL.md; online_trader.md; ignored POSITIVE_OBSERVED_CONFIGS.json; ignored SYMBOL_RUNTIME_AUTHORITY_AUDIT.json; regenerated ignored REPORT.md and STATUS.json
COMMITS = PROJECT_STATE_COMMIT_SELF_RESOLVE_WITH_GIT; DOCUMENTATION_RECONCILIATION_COMMIT_PENDING
PUSH = NOT_PERFORMED
AHEAD_BEHIND = TO_BE_RESOLVED_AFTER_DOCUMENTATION_COMMIT
WORKTREE = TO_BE_RESOLVED_AFTER_DOCUMENTATION_COMMIT

PRODUCTION_TRADING_LOGIC_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO

LIVE_STATE = DISABLED_FALSE
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

OUT_OF_SCOPE_ISSUES = AUTHORITATIVE_EXPECTANCY_R_REMAINS_UNAVAILABLE_IN_ACCEPTED_PERSISTED_DATASET
REMAINING_BLOCKERS = BEST_CANONICAL_RESULT_HAS_3_VALIDATION_TRADES_AND_1_UTC_PERIOD_BELOW_UNCHANGED_20_AND_3; SEARCH_REMAINS_DESCRIPTIVE_ONLY_NOT_CERTIFIED
NEXT_RECOMMENDED_ACTION = SEPARATE_ADAPTIVE_REFINEMENT_TASK_MAY_CONSUME_EXISTING_EXPANDED_SEARCH_HANDOFF_ONLY_IF_EXPLICITLY_AUTHORIZED
```

## Exact ranking forensic

`rank_results` first excludes rows whose `evaluation_status` is not `ACCEPTED`.
It then sorts descending by the tuple returned from `rank_score`:

```text
expectancy_R
profit_factor
-max_drawdown
min(trade_count, validation_minimum_trades)
symbol_coverage
rank_stability
config_id
```

The validation minimum in the capped trade-count component remains the
canonical 20. Eligibility for promotion does not select the observed leader;
all accepted low-sample rows can be research-ranked, while their performance
class remains `INSUFFICIENT_SAMPLE` and validation eligibility remains false.

Net PnL is not part of the ranking tuple. In this campaign every
`expectancy_R` is unavailable and therefore receives the existing common
sentinel. The next discriminator is profit factor. Positive one-trade rows have
no finite PF because they contain no loss, and the unchanged ranking treats
missing PF as zero. The three-trade canonical leader has PF 0.95351674 and is
therefore ranked above the one-trade positive clusters even though its net PnL
is negative. This explains the prior ambiguity without changing ranking.

## Corrected positive accounting

The earlier `POSITIVE_OBSERVED_CONFIGS = 2` field counted positive behavioral
representatives but was named as though it counted numeric configurations.
Reconciliation over the unchanged 500 durable result rows proves:

```text
POSITIVE_NUMERIC_CONFIGS = 108
POSITIVE_BEHAVIORAL_CLUSTERS = 2
POSITIVE_BEHAVIORAL_DUPLICATES = 106
```

`POSITIVE_OBSERVED_CONFIGS.json` retains every positive numeric configuration,
its canonical rank/status, validation eligibility and behavioral signature.
No configuration was re-evaluated; reporting reconciliation reports
`EVALUATIONS_EXECUTED = 0`.

## Universal symbol authority forensic

The static AST audit scanned all ten symbols supplied by the authoritative
`trading-universe-v2` across `traders_ml/parameter_sweep/*.py`. The one former
runtime default was the standalone separability CLI default for DOGEUSDT; it
was removed and `--symbol` is now required. The post-fix result is zero runtime
hardcodes, defaults and symbol-specific branches. Literal occurrences in
research tests and audit evidence are classified separately as allowed
fixtures/artifacts.

The runtime flow is:

```text
GUI dropdown or required CLI --symbol
-> validate_parameter_sweep_symbol against trading-universe-v2
-> run config/checkpoint
-> dataset exact-symbol validation
-> separability manifest/handoff
-> range handoff exact-symbol validation
-> expanded-search config/results
-> resume exact-symbol validation
```

Fixture-level DOGEUSDT and LINKUSDT runs execute the same
`run_expanded_search` path without code changes. Handoff, dataset and resume
mismatches fail closed, and missing/empty/None symbol input produces
`SYMBOL_REQUIRED` rather than selecting a fallback pair.

## Artifacts

```text
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/POSITIVE_OBSERVED_CONFIGS.json
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/REPORT.md
artifacts/scalping_v2_parameter_sweep/expanded_search_dogeusdt_final_01/STATUS.json
artifacts/scalping_v2_parameter_sweep/SYMBOL_RUNTIME_AUTHORITY_AUDIT.json
```
