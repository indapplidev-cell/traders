# TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_VALIDATION_RANKING_01 — FINAL

```text
FINAL_STATUS = PASS
FINAL_VERDICT = PASS_ELIGIBILITY_FIRST_VALIDATION_RANKING_HANDOFF_CREATED_ZERO_ELIGIBLE_VALID_OUTCOME

SYMBOL = DOGEUSDT
PROFILE = trade-5m-v2

SYMBOL_AUTHORITY_SOURCE = app.trading_universe.domain:trading-universe-v2 -> required CLI --symbol -> validate_parameter_sweep_symbol -> fingerprint-bound accepted campaign
RUNTIME_SYMBOL_HARDCODES = 0
RUNTIME_SYMBOL_DEFAULTS = 0
RUNTIME_SYMBOL_BRANCHES = 0

VALIDATION_POLICY_SOURCE = config/research/research_parameters.yaml:ranking through load_validation_sample_policy typed resolver
VALIDATION_MINIMUM_TRADES = 20
MINIMUM_INDEPENDENT_PERIODS = 3
INDEPENDENT_PERIOD_UNIT = UTC_CALENDAR_DAY

CANONICAL_RANKING_COMPARATOR = expectancy_R DESC; profit_factor ranking value DESC; max_drawdown ASC; min(trade_count, validation_minimum_trades) DESC; symbol_coverage DESC; rank_stability DESC; config_id DESC

TOTAL_NUMERIC_CONFIGS = 550
TOTAL_BEHAVIORAL_CLUSTERS = 25

ELIGIBLE_NUMERIC_CONFIGS = 0
ELIGIBLE_BEHAVIORAL_CLUSTERS = 0

DESCRIPTIVE_NUMERIC_CONFIGS = 550
DESCRIPTIVE_BEHAVIORAL_CLUSTERS = 25

POSITIVE_NUMERIC_CONFIGS = 127
POSITIVE_BEHAVIORAL_CLUSTERS = 3

TOP_ELIGIBLE_CONFIG = NONE
TOP_ELIGIBLE_SIGNATURE = NONE

TOP_DESCRIPTIVE_CONFIG = fec017f393fe5daf2b7c5354ab275fc0e1f7190a8c01e7c6c5889b94862d40c5
TOP_DESCRIPTIVE_SIGNATURE = f3bd8181679724f23b7434fe007af0aaa0fb28dc6716c388901eb645d2282e41

TOP_DESCRIPTIVE_TRADES = 1
TOP_DESCRIPTIVE_PERIODS = 1
TOP_DESCRIPTIVE_NET_PNL = 1.01784916
TOP_DESCRIPTIVE_STORED_PF = NOT_AVAILABLE
TOP_DESCRIPTIVE_PF_AVAILABLE = NO
TOP_DESCRIPTIVE_PF_RANKING_VALUE = +INFINITY

ZERO_LOSS_RANKING_SURROGATE_SEMANTICS = wins>0 AND losses=0 AND net_pnl>0 AND stored_PF=NOT_AVAILABLE -> ranking-only +INFINITY; all other missing PF keeps zero sentinel
STORED_PF_MUTATED = NO

EXPECTANCY_AVAILABILITY = NOT_AVAILABLE_FOR_ALL_550_ACCEPTED_CONFIGS_NO_SUBSTITUTE_INFERRED

VALIDATION_RANKING_HANDOFF_CREATED = YES
VALIDATION_RANKING_HANDOFF_FINGERPRINT = e4b7129f5c15ecf9c2b7ad8d0e4fb061d1534f6d46ae7bfda080aca9829432d4

HOLDOUT_READS = 0
HOLDOUT_OPENED = NO
FINALIST_FREEZE_EXECUTED = NO
ADAPTIVE_REFINEMENT_EXECUTED = NO
EXPANDED_SEARCH_RERUN = NO

RANKING_CHANGED = NO
VALIDATION_20_3_CHANGED = NO

SCHEMA_VIOLATIONS = 0
GATE_FALLBACKS = 0
CROSS_SYMBOL_ROWS = 0
RECONSTRUCTED_ROWS_USED = 0

BYTE_DETERMINISM = PASS_TWO_REAL_SELECTED_SYMBOL_RUNS_SEVEN_REQUIRED_ARTIFACTS_ZERO_BYTE_DIFFERENCES
RESUME_GUARDS = symbol; profile; dataset_fingerprint; calibration_split_fingerprint; validation_split_fingerprint; validation_policy_fingerprint; ranking_policy_fingerprint; parameter_registry_fingerprint; range_handoff_fingerprint; expanded_search_fingerprint; adaptive_handoff_fingerprint; adaptive_clusters_fingerprint; adaptive_results_fingerprint

PROMOTION_ELIGIBLE = NO

TESTS = PASS_17_VALIDATION_RANKING_FOCUSED; PASS_264_RESEARCH_BEFORE_FINAL_YAML_MISSING_KEY_TEST; PASS_265_RESEARCH_FINAL
COMPILE = PASS_COMPILEALL_PARAMETER_SWEEP_AND_RESEARCH_TESTS

FILES_CHANGED = traders_ml/parameter_sweep/validation_ranking.py; traders_ml/parameter_sweep/controller.py; traders_ml/parameter_sweep/ui.py; tests/research/test_parameter_sweep_validation_ranking.py; docs/audits/TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_VALIDATION_RANKING_01_FINAL.md; online_trader.md; artifacts/scalping_v2_parameter_sweep/validation_ranking_dogeusdt_01/{VALIDATION_ELIGIBILITY.jsonl,VALIDATION_NUMERIC_RANKING.json,VALIDATION_BEHAVIORAL_RANKING.json,VALIDATION_ROBUSTNESS.json,VALIDATION_RANKING_HANDOFF.json,STATUS.json,REPORT.md}
COMMITS = PROJECT_STATE_3a4f36735c6e59fc548cf7e1cc4fbf84f5f319bd; DOCUMENTATION_COMMIT_RESOLUTION_git_log_-1_--format=%H_--_online_trader.md
PUSH = PROJECT_STATE_PUSHED; DOCUMENTATION_RECONCILIATION_RESOLVED_BY_GIT
AHEAD_BEHIND = 0_0_AFTER_FINAL_PUSH
WORKTREE = CLEAN_AFTER_FINAL_DOCUMENTATION_COMMIT

PRODUCTION_TRADING_LOGIC_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO

LIVE_STATE = DISABLED_FALSE_UNCHANGED
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

OUT_OF_SCOPE_ISSUES = NONE_FOR_VALIDATION_RANKING; EXISTING_PRODUCTION_SOAK_AND_LIVE_BLOCKERS_UNCHANGED
REMAINING_BLOCKERS = ZERO_CONFIGS_PASS_CANONICAL_20_TRADES_AND_3_INDEPENDENT_UTC_DAYS; FINALIST_FREEZE_MUST_PRODUCE_IMMUTABLE_EMPTY_FREEZE_IF_RUN_ON_THIS_ACCEPTED_HANDOFF
NEXT_RECOMMENDED_ACTION = RUN_SEPARATE_STEP8_IMMUTABLE_FINALIST_FREEZE_FROM_THIS_EXACT_VALIDATION_RANKING_HANDOFF_WITHOUT_HOLDOUT_LIFECYCLE_PROMOTION_OR_SEARCH_RERUN
```

## Evidence summary

Validation Ranking consumes the accepted DOGEUSDT range, Expanded Search,
Adaptive Refinement, dataset, and typed policy artifacts without evaluating a
new candidate. It verifies exact symbol/profile identity, canonical dataset and
calibration/validation split fingerprints, range and Expanded Search aggregate
fingerprints, parameter-registry fingerprint, Adaptive input identity, and the
exact membership topology of all 25 behavioral clusters across 550 unique
numeric configs.

Eligibility is resolved before the two ranking lanes. The canonical typed
authority supplies the 20-trade, three-independent-UTC-day policy. Existing
artifact readiness gates for accepted evaluation, single-symbol coverage,
two populated calibration/validation slices, and setup coverage are preserved.
Every config fails multiple readiness gates; this is a valid descriptive-only
result, not an engineering failure.

Both lanes reuse `ranking.rank_results` unchanged. The top descriptive config
has one win, zero losses, positive Net PnL and stored PF `null`; only its
ranking projection serializes the established positive-infinity surrogate as
`+INFINITY`. It remains ineligible because it has one trade, one independent
period, and only one populated slice. The stored result artifacts are not
changed.

The handoff includes only eligible behavioral representatives in its downstream
eligible list, which is empty. A read-only compatibility check through the
existing Freeze handoff validator passed with eligible numeric/behavioral
counts `0/0` and 25 excluded descriptive representatives. No Freeze function
was executed and no Freeze or Holdout artifact was written.
