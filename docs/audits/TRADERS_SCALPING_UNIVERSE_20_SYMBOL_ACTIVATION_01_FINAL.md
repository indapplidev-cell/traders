# TRADERS_SCALPING_UNIVERSE_20_SYMBOL_ACTIVATION_01 — Final evidence

## Decision

```text
FINAL_STATUS = PASS
FINAL_VERDICT = TWENTY_SYMBOL_TRADE_5M_V2_PAPER_UNIVERSE_IMPLEMENTED_TESTED_DEPLOYED_AND_RUNTIME_VERIFIED_WITHOUT_TRADING_POLICY_CHANGE
ACTIVE_PROFILE = trade-5m-v2
MODE = PAPER
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
WAITED_FOR_MARKET = NO
WAITED_FOR_4H_REPORT = NO
```

The change adds independent markets to the existing Scalping pipeline. It does
not change what qualifies as a trade. No YAML, strategy configuration, trading
threshold, selector policy, bootstrap policy, empirical policy, risk sizing,
portfolio concurrency, entry/exit lifecycle, or 15m runtime was changed.

## Exact authoritative universe diff

Canonical source: `app/trading_universe/domain.py::SCALPING_TRADING_UNIVERSE`.
The previous version is retained unchanged as
`LEGACY_TRADING_UNIVERSE_V2`; only the exact legacy 10-symbol argv for
`trade-5m-v2` is bridged to v3. Arbitrary/test/operator scopes and
`trade-15m-v1` are not expanded.

```diff
 BTCUSDT
 ETHUSDT
 SOLUSDT
 BNBUSDT
 XRPUSDT
 LINKUSDT
 DOGEUSDT
 ADAUSDT
 AVAXUSDT
 SUIUSDT
+ZECUSDT
+NEARUSDT
+UNIUSDT
+ENAUSDT
+XLMUSDT
+TRXUSDT
+WLDUSDT
+LTCUSDT
+FETUSDT
+FILUSDT
```

```text
CONFIGURED_UNIVERSE_COUNT = 20
ACTIVE_UNIVERSE_COUNT = 20
ORIGINAL_10_PRESERVED = PASS
NEW_10_CONFIGURED = PASS
DUPLICATES = 0
```

Exact configured order:

```text
BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT,
LINKUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, SUIUSDT,
ZECUSDT, NEARUSDT, UNIUSDT, ENAUSDT, XLMUSDT,
TRXUSDT, WLDUSDT, LTCUSDT, FETUSDT, FILUSDT
```

## Symbol preflight and Binance filter evidence

Authoritative public observation was refreshed at
`2026-09-20T14:14:42.186Z`. All rows passed Binance Spot existence, USDT quote,
TRADING state, precision, PRICE_FILTER, LOT_SIZE, MARKET_LOT_SIZE when supplied,
NOTIONAL/MIN_NOTIONAL, positive book, contiguous closed 1m/5m data, freshness,
and account-commission authority checks.

| Symbol | Status | Reason | tickSize | stepSize | minQty | minNotional | 1m | 5m | Fee authority |
|---|---|---|---:|---:|---:|---:|---|---|---|
| BTCUSDT | PASS | — | 0.01000000 | 0.00001000 | 0.00001000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| ETHUSDT | PASS | — | 0.01000000 | 0.00010000 | 0.00010000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| SOLUSDT | PASS | — | 0.01000000 | 0.00100000 | 0.00100000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| BNBUSDT | PASS | — | 0.01000000 | 0.00100000 | 0.00100000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| XRPUSDT | PASS | — | 0.00010000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| LINKUSDT | PASS | — | 0.00100000 | 0.01000000 | 0.01000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| DOGEUSDT | PASS | — | 0.00001000 | 1.00000000 | 1.00000000 | 1.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| ADAUSDT | PASS | — | 0.00010000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| AVAXUSDT | PASS | — | 0.00100000 | 0.01000000 | 0.01000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| SUIUSDT | PASS | — | 0.00010000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| ZECUSDT | PASS | — | 0.01000000 | 0.00100000 | 0.00100000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| NEARUSDT | PASS | — | 0.00100000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| UNIUSDT | PASS | — | 0.00100000 | 0.01000000 | 0.01000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| ENAUSDT | PASS | — | 0.00010000 | 0.01000000 | 0.01000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| XLMUSDT | PASS | — | 0.00010000 | 1.00000000 | 1.00000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| TRXUSDT | PASS | — | 0.00010000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| WLDUSDT | PASS | — | 0.00010000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| LTCUSDT | PASS | — | 0.01000000 | 0.00100000 | 0.00100000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| FETUSDT | PASS | — | 0.00010000 | 0.10000000 | 0.10000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |
| FILUSDT | PASS | — | 0.00010000 | 0.01000000 | 0.01000000 | 5.00000000 | fresh | fresh | BINANCE_ACCOUNT_COMMISSION_SNAPSHOT |

Disabled table:

| Symbol | Configured | Active | Reason |
|---|---|---|---|
| none | — | — | all 20 passed |

The persisted exact reasons are bounded to:
`SYMBOL_NOT_TRADING`, `SYMBOL_FILTERS_UNAVAILABLE`,
`SYMBOL_BOOK_UNAVAILABLE`, `SYMBOL_1M_DATA_UNAVAILABLE`,
`SYMBOL_5M_DATA_UNAVAILABLE`, `SYMBOL_DATA_STALE`,
`SYMBOL_COMMISSION_UNAVAILABLE`, and `SYMBOL_METADATA_INVALID`.
There is no automatic substitute path and no synthetic filter/default path.

## Account commission proof

```text
SNAPSHOT_TYPE = BINANCE_ACCOUNT_COMMISSION_SNAPSHOT
PROVIDER = binance-spot-account-commission-rest-v1
REAL_ACCOUNT_DATA = true
SYMBOL_COUNT = 20
SNAPSHOT_ID = binance:account-commission:58cbcfde7b665a6afd07707001d20557d8f85b8d9104cb21b37a79a95f7905c8
FETCHED_AT = 2026-09-20T14:14:44.419345Z
STATIC_FALLBACK = NO
SYNTHETIC_COMMISSION = NO
```

The startup refresh reported `READY`, `active_symbols_ready=20`,
`real_account_data=true`, and `stub_active=false`. No credential value appears
in this evidence.

## 1m/5m subscription, storage, freshness, and capacity proof

The market-data and orchestrator health reports both list the same exact 20
symbols with `overall_status=OK` and `last_error=null`. New-symbol storage
contained 1,440 or more 1m rows and 2,016 5m rows per symbol after bounded
warmup. The collector derives the same canonical v3 universe. The preflight
also independently proved contiguous closed candles and fresh 1m/5m tails.

```text
MARKET_DATA_SYMBOLS = 20
ORCHESTRATOR_SYMBOLS = 20
ORCHESTRATOR_PROFILE = trade-5m-v2
PROFILE_OWNER = ACQUIRED
RESTART_STORM = NO; restart_count=0
OOM = NO; OOMKilled=false
QUEUE_STARVATION = NOT_OBSERVED
DB_LOCK_AMPLIFICATION = NOT_OBSERVED
1M_STRATEGY_CREATED = NO
```

The explicit 4h export test generated `48 * 20 = 960` rows and asserted symbol,
profile/runtime identity, and lifecycle-field preservation. This is a load
sanity check, not a trading target.

## Empirical, selector, cost, lifecycle, and 15m proof

All ten new symbols currently have zero natural CLOSED PAPER positions.
Accordingly their symbol-specific natural sample is `0` and authority remains
`NOT_ESTABLISHED`; no old-symbol sample was copied, no cross-symbol history was
mixed, and the existing PAPER bootstrap hierarchy remains responsible for the
normal fallback decision.

The existing deterministic eligible-approval ranking is unchanged. v3 only
widens the candidate set; it adds no priority, round-robin, reserved slot, or
second selector. The production arming scope proves `max_new_commands=1` and
`max_open_positions=1`. New symbols use the same spread, Binance account fee,
slippage, depth impact, adverse reserve, net-edge, net-RR, canonical 1m entry,
STOP/TARGET, causal hold, STALE, NET_PNL_PROTECTION, MAX_HOLD_TIME, close, and
accounting paths.

`trade-15m-v1` remains excluded from the exact-v2 bridge. Its legacy container
is still exited with `restart=no`. No 15m file, schedule, universe, or behavior
was changed.

```text
STRATEGY_CHANGED = NO
TRADING_THRESHOLDS_CHANGED = NO
PARAMETER_TUNING = NO
MAX_OPEN_CHANGED = NO
MAX_NEW_COMMANDS_CHANGED = NO
SELECTOR_POLICY_CHANGED = NO
PORTFOLIO_CONCURRENCY_POLICY_CHANGED = NO
BOOTSTRAP_CHANGED = NO
EMPIRICAL_POLICY_CHANGED = NO
15M_CHANGED = NO
V1_USED = NO
YAML_CHANGED = NO
```

Immutable strategy proof at deployment retained config hash
`4553895fdd0f4beb0244d9a5ccca990fee6c7b672640cf5050c39761e8da82d1`,
`minimum_planned_rr=0.476674`, `min_net_edge_bps=5.0`, and
`bucket_min_sample=20`.

## Schema, activation, and runtime evidence

```text
ALEMBIC = 0034_scalping_universe_v3
UNIVERSE_STATE = trading-universe-v3
PREVIOUS_UNIVERSE_STATE = trading-universe-v2
UNIVERSE_GENERATION = 3
CONTROL_STATE = CONTINUOUS_ARMED
CONTROL_GENERATION = 15
CONTROL_SCOPE_SYMBOLS = 20
LIVE_ALLOWED = false
ACTIVE_OR_CLOSING_POSITIONS_AT_SWITCH = 0
READONLY = healthy
OPERATOR_CONTROL = healthy
PAPER_READINESS = READY; blockers=[]
```

The pre-existing v2 canary was safely stopped before migration. It had no
position but had a stale OPEN entry order repeatedly rejected by an existing
DB check. Normal disable correctly failed closed; the operator control was
transitioned through `EMERGENCY_STOPPED`, the no-position canary was terminally
recorded as `FAILED_SAFE` with
`DEPLOYMENT_PRECHECK_STALE_ENTRY_DB_CHECK_VIOLATION`, and the control returned
to `DISABLED` before v3 activation. No real exchange order was possible.

Runtime images for market data, orchestrator, collector, readonly, and control
were rebuilt. The three revision-bearing services report
`d93d3a55e530f134f623aab8d8238b293b7770d8`; all relevant containers are
running, restart count is zero, and both HTTP services are healthy.

## Tests

```text
CORE_TASK_SUITE = 2979 passed, 1 deselected
FINAL_CHANGED_SCOPE = 2898 passed, 5 skipped, 8 known stale failures
FINAL_V3_EXPORT_PREFLIGHT_SELECTOR = 37 passed, 1 deselected
EMPIRICAL_COST_SELECTOR_15M = 47 passed, 1 deselected
COMPILEALL = PASS
ALEMBIC_OFFLINE_AND_UPGRADE = PASS
EXPORT_20_SYMBOL_LOAD = PASS; 960 rows
```

The eight disclosed failures are pre-existing stale assertions: seven still
request the removed `trade-5m-v1`, and one expects obsolete Alembic predecessor
`0019` instead of the current schema lineage. They are not universe regressions
and were not changed under this task. A separate broader run had 3 unrelated
continuation-fixture failures; the bounded v3 suite passes. User-owned artifact
deletions and the user modification to
`tests/operator_control_production_deployment/test_production_lifecycle_worker.py`
were not staged or changed.

## Changed implementation files and logical commits

Implementation files are the 34 paths in the three commits below: migration and
ORM models; public Binance metadata client; market-data bridge; versioned
universe/preflight/activation; instrument registry; approval/control/continuous
lineage; readonly projection/schema/query; orchestrator and collector wiring;
research derived universe; and their focused tests.

```text
fc9364d39c754dae82b3ae1ef86aa83930e5acb1 feat(scalping): expand paper universe to twenty symbols
001ca1367a016825fcfa16fd001cf054509ea966 fix(scalping): persist v3 continuous lineage
d93d3a55e530f134f623aab8d8238b293b7770d8 fix(migrations): grant universe preflight reads
```

This audit document is the deployment/project-state evidence commit input.
`online_trader.md` is reconciled separately and last, with its own revision
resolved only through Git.
