# Parallel 5m search and dual-profile UI foundation

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_WITH_LIMITATIONS_TRADERS_PARALLEL_5M_SEARCH_AND_DUAL_PROFILE_UI_FOUNDATION_01_SOURCE_READY_DEPLOYMENT_REQUIRED
SERVER_IMPLEMENTATION_COMMIT = 72c04f91fa00bbc422d60f646578d254ef994217
DESKTOP_IMPLEMENTATION_COMMIT = 87727c6b067454653b85eb07023784fc938856fc
DEFAULT_TRADE_PROFILE = trade-15m-v1
SHADOW_TRADE_PROFILE = trade-5m-v1
PRODUCTION_SHADOW_DEPLOYMENT = NOT_ATTEMPTED
PRODUCTION_SCHEMA = 0015_trading_universe_activation
SOURCE_SCHEMA_HEAD = 0017_parallel_trade_profiles
MIGRATION_DEPENDENCY = 0016_control_mobile_device_security_THEN_0017_parallel_trade_profiles
NEXT_ACTION = TRADERS_PARALLEL_5M_SEARCH_SHADOW_RUNTIME_DEPLOYMENT_ACCEPTANCE_01
```

The source foundation introduces profile identity through trigger, pipeline,
store, metrics, health, funnel and Readonly boundaries. Omitted profile remains
the legacy 15m contract. The independent 5m profile uses existing closed market
data and closed higher-timeframe context, has explicit timeframe-aware tuning
and validity, profile-aware idempotency/cursors, bounded concurrent execution,
fault isolation, causal stop/target provenance and an observability-only cost
diagnostic. Its store path cannot invoke PAPER final-approval materialization.

The inactive future arbiter contract shares account equity and global risk,
denies same-symbol double exposure, and classifies opposing directions as
`CROSS_TIMEFRAME_CONFLICT`; it has no execution entry point. The desktop defaults
to 15m and adds selected-profile views only to Overview, Market, Analysis,
Scenarios and Funnel. Trading Pairs, infrastructure incidents and PAPER equity
remain shared. All new visible strings are generated from the server RU/EN
catalog.

## Acceptance evidence

```text
PROFILE_FOCUSED_SERVER_TESTS = 30_PASSED
SERVER_IMPACTED_REGRESSION = 2017_PASSED
DESKTOP_FULL_REGRESSION = 1449_PASSED_2_SKIPPED_3029_SUBTESTS
POSTGRESQL16_MIGRATION_CYCLE = 0016_TO_0017_TO_0016_TO_0017_PASS
HISTORICAL_REPLAY = EXACT10_12_BOUNDARIES_EACH_120_UNIQUE_OPPORTUNITIES_ERRORS0_FUTURE_USAGE0
HISTORICAL_REPLAY_FUNNEL = ANALYSIS120_SETUP2_STRATEGY0_RISK0_FINAL0_COST_DIAGNOSTIC120
PROFITABILITY_CLAIMED = NO
PRODUCTION_READONLY = HEALTHY_27_GET_0_WRITE
PRODUCTION_CONTROL = ARMED_GENERATION6_UNCHANGED
PRODUCTION_CANARY = 6f9858cd-f6b1-4c7f-810c-fccc1065bb9d_WAITING_COMMAND0_POSITION0_UNCHANGED
PRODUCTION_LIVE = OFF_UNCHANGED
PRODUCTION_RESTARTS = 0
PRODUCTION_MUTATIONS = 0
```

The broader historical server collection was also attempted. It was not used
as a PASS claim: the protected environment lacks `cryptography`, and the system
environment produced 30,479 passes, 8 skips, 559 failures and 342 setup errors
across unrelated environment-bound and stale historical suites (including a
pre-existing assertion for schema 0014 while the pre-task source was already at
0015). The impacted 2,017-test regression and focused acceptance are green.

Production activation was deliberately deferred. Applying the new source head
requires the pending 0016 migration followed by 0017 and an independently
deployable 5m worker. Those actions were not authorized here and cannot be
performed while proving zero interruption to the running 15m baseline. No
production migration, container replacement, service restart, Control/canary
mutation, PAPER mutation, Binance private call, LIVE change or push occurred.
