# Parameter Sweep single-symbol search mode fix 01

```text
FINAL_STATUS = PASS
FINAL_VERDICT = SINGLE_SYMBOL_RESEARCH_CAMPAIGN_IDENTITY_FILTERING_REPLAY_RESUME_AND_REPORTING_PASS

SYMBOL_AUTHORITY_SOURCE = app.trading_universe.domain.resolve_universe via traders_ml.parameter_sweep.universe read-only adapter
SYMBOL_AUTHORITY_ID = trading-universe-v2
RESOLVED_SYMBOL_COUNT = 10
RESOLVED_SYMBOLS = BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, LINKUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, SUIUSDT
HARDCODED_PARAMETER_SWEEP_SYMBOL_LIST = NO

GUI_SYMBOL_DROPDOWN = PASS_READONLY_COMBOBOX_FROM_AUTHORITATIVE_RESOLVER_START_DISABLED_UNTIL_VALID_SELECTION
CLI_SYMBOL_ARGUMENT = PASS_EXPLICIT_--symbol_REQUIRED_FOR_NEW_RUN
GUI_CLI_SYMBOL_PARITY = PASS_SHARED_CONTROLLER_ENGINE_CANONICAL_SYMBOL_VALIDATOR_AND_RUN_CONFIG

SMOKE_SYMBOL_1 = LINKUSDT
SMOKE_SYMBOL_1_DATASET_DISTINCT_SYMBOLS = [LINKUSDT]
SMOKE_SYMBOL_1_EVALUATED_SYMBOLS = [LINKUSDT]

SMOKE_SYMBOL_2 = BTCUSDT
SMOKE_SYMBOL_2_DATASET_DISTINCT_SYMBOLS = [BTCUSDT]
SMOKE_SYMBOL_2_EVALUATED_SYMBOLS = [BTCUSDT]

CROSS_SYMBOL_CONTAMINATION = 0_GUARD_FAILS_CLOSED_WITH_CROSS_SYMBOL_CONTAMINATION
NON_SELECTED_SYMBOL_REPLAY_WORK = 0

RUN_CONFIG_SYMBOL = PASS
STATUS_SYMBOL = PASS
REPORT_SYMBOL = PASS
MANIFEST_SYMBOL = PASS_DATASET_AND_RUN_MANIFEST
CHECKPOINT_SYMBOL = PASS
FINALIST_FREEZE_SYMBOL_SUPPORT = PASS

SAME_SYMBOL_RESUME = PASS
DIFFERENT_SYMBOL_RESUME = FAIL_CLOSED_RESUME_SYMBOL_MISMATCH

SINGLE_SYMBOL_COVERAGE_SEMANTICS = PASS_EXPECTED1_COVERAGE1_NO_MULTI_SYMBOL_REJECTION
EXISTING_MODE_REGRESSION = PASS_ALL_6_MODES_EXACTLY_ONE_SELECTED_SYMBOL

TESTS = PASS_151_RESEARCH_TESTS_IN_93.29_SECONDS; PASS_19_FINAL_FOCUSED_TESTS_IN_8.43_SECONDS
COMPILE = PASS_PYTHON_COMPILEALL_TRADERS_ML_PARAMETER_SWEEP_AND_TESTS_RESEARCH

FILES_CHANGED = tests/research/test_parameter_sweep_single_symbol.py; tests/research/test_scalping_v2_parameter_sweep.py; traders_ml/parameter_sweep/artifact_v2.py; traders_ml/parameter_sweep/checkpoint.py; traders_ml/parameter_sweep/cli.py; traders_ml/parameter_sweep/controller.py; traders_ml/parameter_sweep/engine.py; traders_ml/parameter_sweep/historical_replay.py; traders_ml/parameter_sweep/integrity.py; traders_ml/parameter_sweep/research_protocol.py; traders_ml/parameter_sweep/state.py; traders_ml/parameter_sweep/ui.py; traders_ml/parameter_sweep/universe.py; docs/audits/TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_SEARCH_MODE_FIX_01_FINAL.md; online_trader.md
COMMITS = PROJECT_STATE_748b087aff8f6eeb6e3c62b44b25afd21afe7fdb; DOCUMENTATION_RECONCILIATION_RESOLVE_WITH_git_log_-1_--format=%H_--_online_trader.md
PUSH = PROJECT_STATE_PUSHED; DOCUMENTATION_RECONCILIATION_TO_BE_PUSHED_AS_FINAL_TASK_STEP
AHEAD_BEHIND = 0/0_AFTER_PROJECT_STATE_PUSH
WORKTREE = CLEAN_AFTER_FINAL_DOCUMENTATION_COMMIT_AND_PUSH

PRODUCTION_TRADING_LOGIC_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
TRADING_UNIVERSE_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO

LIVE_STATE = FALSE_FRESH_READONLY_API_2026-09-12T06:59:14.059Z
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

FULL_UNIVERSE_AVAILABLE_SYMBOLS = 10
SELECTED_SYMBOLS = 1
EVALUATED_SYMBOLS_PER_CONFIG = 1
NON_SELECTED_SYMBOL_REPLAY_WORK = 0

REMAINING_BLOCKERS = NONE_FOR_SINGLE_SYMBOL_MODE; LARGE_OPTIMAL_SEARCH_INTENTIONALLY_NOT_RUN
NEXT_RECOMMENDED_ACTION = START_A_SEPARATE_DEEP_RESEARCH_CAMPAIGN_FOR_ONE_OPERATOR_SELECTED_SYMBOL_WITHOUT_PARAMETER_PROMOTION_OR_PRODUCTION_MUTATION
```

The two smoke runs use one shared mixed-symbol offline fixture. Filtering occurs
before split, replay, planning, and evaluation. The resulting frozen snapshots,
manifest symbol sets, compact results, checkpoints, reports, and finalist
freezes contain only the requested symbol. PostgreSQL loading applies the same
symbol predicate to opportunity observations, persisted plans, commands,
positions, candles, and time-stop diagnostics; shared inventory counts are
explicitly labelled as storage inventory and are not replayed.

Fresh read-only runtime corroboration found the Readonly API and Operator
Control containers healthy with restart count zero. The PAPER readiness response
reported `live_allowed=false`. No deployment, service restart, order call, DB
write, configuration promotion, or production-universe mutation was performed.
