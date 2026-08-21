# Trading-universe timeout remediation — final evidence

```text
TASK = TRADERS_DESKTOP_TRADING_UNIVERSE_TIMEOUT_REMEDIATION_01
FINAL_VERDICT = PASS
RECONCILED_AT_UTC = 2026-08-21T15:52:45Z
SERVER_IMPLEMENTATION_COMMITS = ab9a89ce5738d93a56316d3a4b7ef77901e3c3e7,06fa6a0c15812df0b71982158962fa07a8cb5d84,700948a23aa78590d6a235bc5a40df7d44ecd7e5,0332a7171e8b1167e10de5921f0a3d2e39eee008,de031bb2fc0faaac10bdd55d8fffea5bb23ef6a4
CLIENT_IMPLEMENTATION_COMMIT = 9ebdf783e053259c115610e27a49bf0b9ab1bc29
CLIENT_STATUS_COMMIT = 584d8738dfa2ac5b12deed1c5ea27feaec3e94bb
```

## Root cause

The three screenshots show cached/last-successful page content together with a
failed current refresh. Production logs contained completed HTTP 200 requests,
then the definitive failure:

```text
psycopg.OperationalError: FATAL: too many connections for role "traders_readonly_api"
```

The failure was produced by four reinforcing defects:

1. `/trading-universe` made separate candle-count queries and materialized the
   full matching pipeline-run history before choosing ten latest rows.
2. the production 5m funnel loaded a four-hour, 490-row JSON history and then
   issued ten redundant per-symbol approval reads on every refresh;
3. the SQLAlchemy pool allowed overflow beyond the PostgreSQL role limit of ten;
4. the desktop used the same five-second timeout for lightweight and computed
   aggregate projections.

At failure time the Readonly container was also measured at `255.8 MiB / 256
MiB`; the persisted 5m result set was `7.51 MiB` before ORM/JSON expansion.
This caused cold-read memory pressure, long-held transactions and a retry queue.

## Remediation

- Trading-universe readiness now uses one unioned candle-count query and a SQL
  `row_number()` latest-per-symbol query: three bounded DB round trips total.
- The funnel reuses its already-loaded atomic run/result pairs for the exact
  authoritative approval classifier and caches only those source rows for 30
  seconds. Validity, eligibility and winner selection still recalculate against
  each request's current time.
- The Readonly engine uses `max_overflow=0`; its configured pool of five cannot
  exceed the role budget.
- Only the Readonly API was right-sized from 0.5 CPU / 256 MiB to 1 CPU / 512
  MiB. PostgreSQL, both orchestrators, Control and PAPER execution were not
  restarted or changed.
- The desktop uses a bounded 10-second budget only for trading-universe and
  funnel projections; ordinary reads retain the configured five seconds.

## Acceptance evidence

```text
READONLY_CONTAINER = c4c41999e97d07b4ddeea37176f2dcf74a8473888bc14dd27255dbec23500e89
READONLY_IMAGE = sha256:ec0f6eca614718991be73510434cbb5ab9bdb03fdc263160c5fa1dcf01d5f6dc
READONLY_SOURCE_IDENTITY = sha256:e38423420c1769bad7f0abb49ab8a74beb1e9116faeb9db652fa71c6f04e150a
READONLY_HEALTH_RESTARTS = HEALTHY_0
READONLY_RESOURCES = 1_CPU_512_MIB
READONLY_CONNECTIONS_AFTER_ACCEPTANCE = 1
SCHEMA = 0018_promote_5m_production_search
TRADING_UNIVERSE_6_SAMPLES = HTTP200_1.095_TO_1.654_SECONDS
COLD_5M_FUNNEL = HTTP200_1.540_SECONDS
WARM_5M_FUNNEL = HTTP200_0.039_TO_0.049_SECONDS
15M_FUNNEL = HTTP200_0.550_SECONDS
DIRECT_DESKTOP_PROVIDER = UNIVERSE_10_IN_1.174_SECONDS_5M_10_OF_10_IN_0.039_SECONDS
SERVER_FOCUSED = 1451_PASSED
SERVER_API_REGRESSION = 130_PASSED_7_SKIPPED
CLIENT_FOCUSED = 27_PASSED_21_SUBTESTS
CLIENT_FULL_ASSERTIONS = 1453_PASSED_2_SKIPPED_3029_SUBTESTS
CLIENT_TCL_ENVIRONMENT_NOTE = INTERMITTENT_EXISTING_TCL_FILE_READ_FAILURE_AFFECTED_TEST_PASSED_IN_ISOLATION
COMPILE_DIFF_CHECK = PASS
```

Fresh production state remained `health=OK`, 5m `CURRENT 10/10`, schema 0018,
Control `ARMED generation 6` with the same waiting canary, account 100 USDT and
zero commands/orders/fills/positions. No PAPER or LIVE mutation occurred.

