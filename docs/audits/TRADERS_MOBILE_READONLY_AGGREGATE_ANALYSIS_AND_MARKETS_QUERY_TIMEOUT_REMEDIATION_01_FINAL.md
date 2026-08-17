# Readonly aggregate Analysis and Markets query timeout remediation 01

## Decision

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_MOBILE_READONLY_AGGREGATE_ANALYSIS_AND_MARKETS_QUERY_TIMEOUT_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
PROJECT_STATE_COMMIT = 6701a01be10ebabf01ba2126d974d9d6a652c4d4
SCHEMA_CHANGE_REQUIRED = NO
PRODUCTION_DEPLOYMENT_PERFORMED = NO
NEXT_ACTION = TRADERS_MOBILE_READONLY_API_PARITY_RUNTIME_REDEPLOYMENT_ACCEPTANCE_02
```

## Failure path and root cause

`GET /api/v1/analysis` routes through
`app/server_api/routes/v1.py::list_analysis`,
`ApiQueryService.analyses`, and
`SqlAlchemyReadAdapter.list_latest_analyses`. Desktop Market routes through
`traders-client/src/traders_client/application/app_controller.py::load_market`
and `ServerProvider.list_markets` to `GET /api/v1/markets`; server
`ApiQueryService.markets` calls that same repository method for the active
analysis projection. The timeouts therefore share one canonical query root.

The previous SQL joined all eligible history for the ten active symbols,
performed repeated JSON eligibility extraction, sorted a
`ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY closed_until_ms DESC, ...)`
window, and applied `row_number = 1` and `LIMIT 10` only afterwards. Production
plain `EXPLAIN` showed an `online_pipeline_results` sequential scan followed by
sort/window work, total cost 2321.49. The results relation was approximately
7,253 rows but 109 MB because each row carries several JSON projections; the
runs relation was approximately 7,625 rows and 10 symbols.

Root-cause classification:

```text
WINDOW_OVER_FULL_HISTORY
FULL_SORT_BEFORE_LIMIT
LATE_LIMIT
UNBOUNDED_HISTORY_SCAN_WITHIN_ACTIVE_SYMBOL_SET
```

## Remediation and semantics

The batch method now emits one SQL request containing at most ten `UNION ALL`
branches. Each branch is fixed to one active symbol, walks the existing
`uq_online_pipeline_window (symbol, primary_timeframe, closed_until_ms)` index
backward, checks a correlated result through the unique `run_id` lookup, and
stops at the first eligible row. No Python-side history materialization, N+1
database request, retry, timeout increase, cache or migration was introduced.

Single-symbol and aggregate reads now share one canonical eligibility predicate
helper. The schema uniquely identifies a run boundary per symbol/timeframe and
one result per run, so boundary ordering preserves the previous authoritative
latest and deterministic tie semantics. Closed-candle, freshness, direction,
regime, impulse, phase, entry quality, status and source identities are
unchanged.

## Plans and performance

Production metadata/read-only diagnostics used `BEGIN READ ONLY`, a reduced
local statement timeout and no DDL/DML. The new SQL was safe to execute with
`EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)` after plain plan inspection:

```text
rows = 10/10
planning = 13.462 ms
execution = 93.510 ms
plan cost = 362.23..362.26
top sort = quicksort 25 kB
latest branches = 10 backward index scans on uq_online_pipeline_window
online_pipeline_results sequential scans = 0
```

An isolated PostgreSQL 16 container held 100,000 runs and 100,000 results over
10 symbols, with a 2 KiB padding field in each analysis JSON. It was removed
after the benchmark. Exact observations:

```text
old query = 17,197.433 ms, one deterministic sample
new query = 7 samples
new samples ms = 74.569, 35.611, 42.882, 53.063, 32.424, 34.527, 31.403
new median = 35.611 ms
new max = 74.569 ms
```

No percentile claim is made from seven samples.

## Verification

```text
focused repository/semantic/bound tests = 14 passed
server API and PAPER impacted regression = 1932 passed
security/scanner regression = 618 passed
desktop provider/contract regression = 29 passed, 12 subtests passed
source route inventory = 25 GET / 0 write
compileall app/server_api = pass
desktop source changed = no
mobile source changed = no
```

The server, Control API and PostgreSQL production containers remained healthy
with restart count zero; listeners remained loopback-only on 8765 and 8766 and
18765 remained absent. Fresh read-only state showed schema 0015 and the current
nonterminal canary persisted as `NO_ELIGIBLE_APPROVAL`, generation 6, with zero
commands and zero positions. The task made no production deployment, schema,
database data, Control, trading, canary, LIVE or Binance-order mutation.

The deployed runtime still contains the old query and must not be described as
fixed until the next narrow Readonly rebuild/recreate and acceptance rerun.
