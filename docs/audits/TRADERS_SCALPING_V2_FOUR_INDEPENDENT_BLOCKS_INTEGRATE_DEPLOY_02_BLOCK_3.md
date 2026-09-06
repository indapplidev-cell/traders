# TRADERS_SCALPING_V2_FOUR_INDEPENDENT_BLOCKS_INTEGRATE_DEPLOY_02 — BLOCK 3

TASK_STATUS = BLOCK_3_COMPLETE
FINAL_VERDICT = PASS
RECONCILED_AT_UTC = 2026-09-06T21:01:13.449Z

## Result

BLOCK_3_IMPLEMENTED = YES
BLOCK_3_INTEGRATED = YES
BLOCK_3_DEPLOYED = YES
BLOCK_3_RUNTIME_ACTIVE = YES
BLOCK_3_MODE = SHADOW
BLOCK_3_PERSISTENCE = PASS
BLOCK_3_POSTGRES_E2E = PASS
BLOCK_3_PRODUCTION_EXIT_MUTATIONS = 0
BLOCK_3_PUSHED = YES

The real call path is:

`OPEN PAPER position -> production lifecycle -> closed 1m market/current Binance-account costs -> stale-position SHADOW evaluator -> PostgreSQL diagnostic -> Readonly funnel projection -> Desktop`.

The evaluator uses authoritative `paper_positions.opened_at`. It computes LONG/SHORT target progress, MFE/MAE, gross PnL, net exit PnL after incurred entry fee plus current real-account exit commission, spread, slippage and adverse reserve, and cost-aware net break-even. Its output cannot enter the production exit mutation request.

## Authoritative policy

CONFIG_SOURCE = config/trading/trade_parameters.yaml
RUNTIME_CONFIG_HASH = 0485c11f0071dba01a0a32aa797875d8fdbdeeffa339c20d8baf9e4470d04c90
TIME_STOP_MODE = SHADOW
SOFT_TIMEOUT_SECONDS = 600
HARD_TIMEOUT_SECONDS = 900
MIN_TARGET_PROGRESS = 0.20
MIN_MFE_BPS = null
MIN_REMAINING_EV_R = 0.0
EXTENSION_SECONDS = 300
MAX_EXTENSIONS = 1
NET_BREAK_EVEN_PROTECTION = ENABLED_AT_TARGET_PROGRESS_0.50
CURRENT_EXIT_COSTS = TRUE

The 900-second hard timeout is an absolute cap. The single 300-second extension covers the interval from the 600-second soft timeout to that hard cap.

## Persistence and tests

SCHEMA_HEAD = 0029_stale_position_shadow
PERSISTENCE_TABLE = scalping_stale_position_shadow_diagnostics
RUNTIME_ROLE_SELECT_INSERT_UPDATE = PASS
READONLY_ROLE_SELECT = PASS
ISOLATED_MIGRATION_BASE_TO_0029 = PASS
ISOLATED_SCHEMA_COMPATIBILITY = PASS
ISOLATED_POSTGRES_16_E2E = PASS
E2E_POSITION_AFTER_SOFT = OPEN
E2E_POSITION_AFTER_HARD = OPEN
E2E_DIAGNOSTIC_ROWS = 2
E2E_COMMAND_MUTATIONS = 0
E2E_ACCOUNTING_MUTATIONS = 0
E2E_REAL_ORDER_CALLS = 0

Focused verification after the final implementation:

- stale/cost/funnel/i18n/lifecycle/schema/preparation: 88 passed;
- final stale/funnel/i18n/lifecycle/schema set: 61 passed;
- operator composition regression after the discovered wiring fault: 19 passed;
- Desktop stale parser test: PASS;
- Desktop RU/EN stale diagnostics GUI test: PASS;
- server and Desktop `compileall`: PASS;
- `git diff --check`: PASS.

The broad Desktop run reached 138 passed and 2 skipped before a local Tcl/Tk installation error (`fonts.tcl` initialization) stopped it. The directly affected GUI test passed independently after that environment-only failure.

## Deployment and running acceptance

SERVER_IMPLEMENTATION_COMMIT = 337124ca6e45a239b3113a487877bdca21f44fa4
SERVER_WIRING_FIX_COMMIT = 4cf697515a99d4ba283cf7f3c1853c81bb468546
DESKTOP_COMMIT = 5371f796b36b41f56075f10d94c7629227733d1f
SERVER_PUSH = PASS
DESKTOP_PUSH = PASS

WORKER_IMAGE = sha256:df2d15bf9fa549735df6b97b082901f64e7b40ffe170c1453ca01ad026252d8c
WORKER_SOURCE_REVISION = 337124ca6e45a239b3113a487877bdca21f44fa4
READONLY_IMAGE = sha256:fa264133bef70841078658f53afd5726ef3674252955d04954d55ed05bfdbf21
READONLY_SOURCE_REVISION = 337124ca6e45a239b3113a487877bdca21f44fa4
OPERATOR_IMAGE = sha256:484a04ff8160b9eeeb221a840c13df44db9ff004abb6cbb5f7c6efcab48c7045
OPERATOR_SOURCE_REVISION = 4cf697515a99d4ba283cf7f3c1853c81bb468546

WORKER_RUNNING = YES
READONLY_HEALTH = HEALTHY
OPERATOR_HEALTH = HEALTHY
OPERATOR_RESTART_COUNT = 0
READONLY_STALE_CAPABILITY = STALE_POSITION_SHADOW
READONLY_STALE_RUNTIME_ACTIVE = TRUE
READONLY_STALE_LATEST = null
READONLY_LATEST_NULL_ACCEPTED = YES_NO_NATURAL_TRADE_WAIT_REQUIRED
COMMISSION_SOURCE = BINANCE_ACCOUNT_COMMISSION
COMMISSION_ACTIVE_SYMBOLS_READY = 10/10
COMMISSION_REAL_ACCOUNT_DATA = TRUE
COMMISSION_STUB_ACTIVE = FALSE

An initial operator deployment exposed an invalid reference to fields absent from `RuntimeProfileParameters`. It was not accepted. Commit `4cf697515a99d4ba283cf7f3c1853c81bb468546` reuses the already-authoritative scalping cost source and adds a composition regression; the rebuilt operator then became healthy with zero restarts.

## Safety invariants

PRODUCTION_COUNTS_BEFORE = commands=54,orders=106,positions=53
PRODUCTION_COUNTS_AFTER = commands=54,orders=106,positions=53
PRODUCTION_EXIT_BEHAVIOR_CHANGED = NO
PRODUCTION_DIAGNOSTIC_ROWS_AT_ACCEPTANCE = 0
ACTIVE_PAPER_PROFILE = trade-5m-v2
SCALPING_V1_ACTIVE = NO
TRADE_15M_ENABLED = NO
LEGACY_15M_CONTAINER = STOPPED_EXITED_0
ONE_MIN_MODE = SHADOW
LIVE = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0

The running database contains one pre-existing OPEN PAPER position, but no natural-trade wait or forced production signal was performed. Runtime acceptance therefore relies on the active running capability plus the deterministic isolated PostgreSQL lifecycle E2E, exactly as allowed by the task.

## Desktop

DESKTOP_PROCESS_ID_AT_ACCEPTANCE = 6664
DESKTOP_COMMAND = python -m traders_client
DESKTOP_PROVIDER = PRODUCTION_READONLY_HTTP
DESKTOP_SERVER_URL = http://127.0.0.1:8765
DESKTOP_LOCALE = ru
DESKTOP_FIELDS = mode,holding,soft_timeout,hard_timeout,target_progress,current_net_exit_pnl,shadow_decision,shadow_exit_reason
