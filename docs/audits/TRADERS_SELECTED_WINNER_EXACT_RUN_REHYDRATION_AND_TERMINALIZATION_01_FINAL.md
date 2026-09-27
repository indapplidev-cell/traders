# Selected-winner exact-run rehydration and terminalization 01

## A. Prior state

The preceding remediation had already delivered durable selector identity,
bounded continuation polling, true 1h/4h aggregates, a 20-symbol barrier,
warm readiness below one second, and natural PAPER
SELECTED -> COMMAND -> OPEN -> CLOSED evidence. This task did not reopen or
change those contracts. Production history was read only; no row was updated,
deleted, backfilled, replayed, archived, or replaced. No retention, pool,
timeout, cadence, TTL, causal window, or database schema change was used.

Project-state implementation and deployment revision:
`214feb1d2e7691eb04c45eb2fdb1aaf015a2db6d`.

## B. Natural cases

Canonical PostgreSQL timestamps supersede the UI's last-update impression.

| Case | Plan / cycle | Selected | Claim / terminal | Proven interpretation |
|---|---|---|---|---|
| XLMUSDT 18:35Z | plan 18:35:53.349Z; cycle complete 18:35:53.404506Z | 18:36:01.755171Z, already 1.755s beyond the +60s causal deadline | claim and `ENTRY_FILL_WINDOW_MISSED` 18:36:01.784179Z | canonical terminal was +61.784s, not +301s; a later 18:40:01.445Z rediscovery updated display-facing timestamps |
| SOLUSDT 19:05Z | plan +48.875s; cycle complete 19:05:49.432102Z | 19:05:56.638013Z; 3.362s causal headroom | claim 19:05:56.664044Z; terminal 19:06:00.280798Z | canonical terminal was +60.281s, not +303s; later 19:10:03.240Z rediscovery produced the UI illusion; required SHADOW refinement became ready only at 19:06:15.755Z |
| XRPUSDT 19:10Z | plan +23.980s; cycle complete 19:10:24.226322Z | 19:10:45.729570Z; 14.271s causal headroom | claim 19:10:45.809478Z; terminal 19:11:00.209173Z | canonical terminal was +60.209s, not near the 19:14:59.999Z plan TTL; later 19:15:01.999Z rediscovery changed the last-update impression; SHADOW refinement became ready at 19:11:19.017Z |

The apparent XRP `13.4s` lookup was not one lookup. The first pending timestamp
was compared with the last overwritten `read_by_run_id_at`. Readonly access
logs contain successful HTTP 200 readiness calls throughout the interval
(19:10:46.36Z, 47.62Z, 48.70Z, 49.82Z, 51.32Z through 59.49Z), proving that
multiple continuation ticks completed. SOL has the same pattern at
19:05:57.047Z, 58.029Z and 59.590Z. Exact response bodies were not historically
persisted, so a more specific historical readiness subreason cannot be
manufactured after the fact.

## C. Exact-run query

The execution reader now performs one exact join through `run_id` and asks
PostgreSQL for only execution-required JSON keys. It has no historical filter,
`ORDER BY`, `LIMIT`, relationship fan-out, selector rerun, latest-symbol lookup,
or UI/export projection. The authoritative indexes are
`uq_online_pipeline_runs_run_id` and `uq_online_pipeline_results_run_id`.

Representative safe read-only production `EXPLAIN (ANALYZE, BUFFERS)` for the
minimal projection:

```text
Nested Loop Left Join (actual time=83.699..85.988 rows=1 loops=1)
  online_pipeline_runs unique-index path: rows=1, shared hit=4
  online_pipeline_results unique-index path: rows=1, shared hit=4
  Buffers: shared hit=393 read=1
Planning Time: 9.735 ms
Execution Time: 86.220 ms
```

The higher buffer count is JSONB/TOAST key extraction on the one result row,
not a table scan. A full-row control query also used both unique indexes and
returned one row (execution 0.675ms on a warm plan), but transferred and decoded
the complete result payload. Natural rows were about 80KB stored and about
570KB as JSON text. The fix keeps existing authoritative tables and performs
server-side minimal JSON object construction.

## D. Rehydration latency decomposition

The deployed operator image was benchmarked read-only for 25 exact XRP run
reads. Results include the transaction-control query, DB clock read, exact row
query, transfer/decode, and reconstruction:

```text
DB_POOL_WAIT_P50_MS = 0.125
DB_POOL_WAIT_P95_MS = 0.201
SQL_FETCH_TRANSFER_JSON_DECODE_P50_MS = 223.985
SQL_FETCH_TRANSFER_JSON_DECODE_P95_MS = 427.397
TOTAL_EXACT_RUN_REHYDRATION_P50_MS = 246.146
TOTAL_EXACT_RUN_REHYDRATION_P95_MS = 498.334
TOTAL_EXACT_RUN_REHYDRATION_MAX_MS = 796.676
MEASURED_STATEMENT_COUNT = 3
EXACT_JOIN_ROWS = 1
```

PostgreSQL/psycopg does not expose independent per-request network-transfer,
TOAST-decompression, JSONB-decode, and ORM-hydration clocks. The narrowest
honest approximation is the combined `sql_fetch_decode` interval above;
`EXPLAIN` buffers corroborate one-row TOAST work. The minimal row is explicitly
reconstructed and has no ORM relationship hydration or related-row lookup.
Instrumentation now persists request, pool, SQL start/end, row decode,
projection ready, Python reconstruction, total time, query count, and first as
well as latest retry evidence.

The isolated PostgreSQL deterministic restart-boundary test persists selection
and the active cycle first, makes required 1m data locally available and
readiness READY, then asserts exact rehydrate-to-command below 2 seconds. It
passed. This was one acceptance run, so percentile labels for selected-to-
command are intentionally not fabricated.

## E. Deadline semantics

`CAUSAL_ENTRY_DEADLINE` is
`paper_plan_execution_outcomes.boundary_closed_at_ms + 60_000`; it is the end
of the only legal next closed-1m entry-fill window. `PLAN_VALID_UNTIL` is
`approval_valid_until_ms`, copied from the approval's broader plan TTL. The
former answers when causal entry becomes impossible; the latter answers when
the plan ceases to be generally valid.

Previously the canonical claim path could record the causal miss promptly,
but terminal rows remained discoverable because `unconsumed_candidates`
excluded only commands and `NOT_SELECTED`. Repeated discovery updated
`updated_at` until plan TTL and created the pending/UI illusion. The store now
excludes every terminal state and, before any exact retry or broad selector
formation, terminalizes an uncommanded selected winner immediately when actual
wall time exceeds the causal deadline. It does not terminate while a required
1m close can still legally arrive.

## F. Readiness reason provenance

SOL and XRP continuation requests received repeated HTTP 200 readiness
responses; there is no evidence of an HTTP timeout. The old adapter converted
any non-ready envelope/semantic check into `READONLY_RUNTIME_NOT_READY` and
`record_attempt` also wrote that downstream execution error into
`selector_reason`. At the same time, the on-host runtime-health artifact was
fresh and reported enabled runtime, DB durability, and active workers. The
best evidence-backed classification is `C_STALE_READINESS_SNAPSHOT` plus
`G_UI_EXPORT_FIELD_SEMANTICS_BUG`; the exact historical denial list cannot be
recovered because response bodies were not stored.

HTTP 200 well-formed envelopes are now authoritative even when mutation is
denied. Their exact `current_mutation_denial_reasons` are preserved. Timeout,
request failure, invalid response, schema/accounting/runtime/control mismatch,
market, approval, WAL and PITR failures receive distinct typed reasons.
Selector reason remains selector-only; `execution_gate_reason`,
`readiness_reason`, `terminal_reason`, and refinement details are separate and
exported compatibly.

## G. Minimal fix

- exact unique-index `run_id` join with a minimal server-side execution JSON projection;
- first/latest exact-read telemetry plus component timings;
- durable terminal-state exclusion from subsequent discovery;
- causal-deadline terminalization before retry/selection;
- exact readiness reason mapping and separate reason-field semantics;
- no cache/materialized authority, migration, infrastructure tuning, or policy change.

## H. Tests

- compile: PASS;
- focused outcome/readiness: 13 passed;
- exact-run, 500-row large-history/32KB TOAST, and 20-symbol PostgreSQL E2E: 3 passed;
- legitimate refinement wait, expiry, expired approval, and no rank-2 fallback: 3 passed;
- approval/outcome/Funnel/export regression group: 1499 passed;
- restart/crash replay, concurrent claim, readiness semantic subset: 5 passed;
- deterministic durable-selected exact continuation: PASS, one command, all losers immediately `LOWER_SELECTOR_RANK`, selected-to-command `<2s`;
- duplicate command identity groups in production after deployment: 0.

A broader legacy collection retained three already-known stale
continuation/current-date readiness fixtures; another unrelated route inventory
failure overlaps a user-owned modified test file. The task-owned focused and
PostgreSQL gates pass, and that user work was neither staged nor changed.

## I. Production smoke

Only `readonly-api` and `operator-control-api` were rebuilt and force-recreated.
No other service was rebuilt or restarted. Both are healthy with source
identity `214feb1d2e7691eb04c45eb2fdb1aaf015a2db6d`.

```text
READONLY_IMAGE = sha256:740029bb6e7decc7d9e723e0b7dd898acee98bfea70dca82f5aa77db154c7cc6
OPERATOR_IMAGE = sha256:067b09c37cb9716e15c41cb6401b5cd267aae89fc64a92784a84f6bddd2b3f03
READINESS = READY; current_mutation_ready=true; denials=[]
CONTROL = CONTINUOUS_ARMED; generation=15; healthy
COMMISSION = READY; 20/20
LATEST_CYCLE_SYMBOLS = 20
LIVE_ALLOWED = false
READINESS_WARM_P50_MS = 380.63
READINESS_WARM_P95_MS = 592.03
NATURAL_POST_FIX_WINNER = NOT_OBSERVED_DURING_BOUNDED_SMOKE
POST_FIX_COMMANDS = 0
REAL_BINANCE_ORDER_CALLS = 0
ALEMBIC = 0035_scalping_v2_ingestion_policy_contract
```

## J. Invariants

Strategy, structural setup, geometry, target, stop, RR, cost model, commission
policy, risk, selector ranking, portfolio limits, maximum open positions,
maximum new commands, plan TTL, causal entry window, exit policy, net-PnL
protection, universe, 15m, LIVE, and real Binance order authority were not
changed. Funnel and true 1h/4h aggregates show no regression. No new 1h, 4h,
or 12h Funnel collection was performed.

## Final verdict

`PASS`: all hard gates are evidenced. The original `13.4s` premise was an
overwritten-last-retry telemetry artifact, while full result hydration was a
real avoidable cost. The deployed exact path remains durable, indexed,
restart-safe, bounded under retained history, terminates by causal semantics,
and preserves exact readiness provenance.
