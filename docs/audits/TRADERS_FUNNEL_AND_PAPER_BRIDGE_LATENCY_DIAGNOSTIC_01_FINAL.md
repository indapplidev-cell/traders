# Traders funnel and PAPER bridge latency diagnostic 01

```text
TASK = TRADERS_FUNNEL_AND_PAPER_BRIDGE_LATENCY_DIAGNOSTIC_01
FINAL_STATUS = BLOCKED
FINAL_VERDICT = SERVER_SIDE_FUNNEL_MATERIALIZATION_AND_SYNCHRONOUS_READONLY_READINESS_BLOCK_CURRENT_DESKTOP_REFRESH_AND_NATURAL_PAPER_EXECUTION
MODE = READ_ONLY_DIAGNOSTIC
CODE_CHANGED = NO
DEPLOYMENT_CHANGED = NO
DATABASE_CHANGED = NO
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
```

## Trading Funnel path

The Desktop client performs one `GET /api/v1/trading/funnel?trade_profile=trade-5m-v2`
for the active Trading Funnel page. It correctly runs the request outside the Tk
thread, coalesces same-scope work, and does not overlap an in-flight page refresh.
However, the page interval is 10 seconds, the transport timeout is 60 seconds,
and a separate health request can occupy the second member of the two-thread
worker pool. The current uncommitted client changes only sort rendered rows and
add translations/tests; they do not add network calls or explain the latency.

Production measurements on 2026-09-27:

```text
FUNNEL_RUN_1 = HTTP_500_AFTER_41888_MS
FUNNEL_RUN_2 = HTTP_500_AFTER_30048_MS
FUNNEL_RUN_3 = HTTP_500_AFTER_30057_MS
ERROR = psycopg.errors.QueryCanceled: canceling statement due to statement timeout
FAILURE_LOCATION = app/server_api/trading_funnel.py:_load_rows/session.execute
HEALTH = 564_TO_1465_MS
TRADING_UNIVERSE = 3002_TO_4713_MS
PAPER_RUNTIME_STATUS = 14040_TO_16223_MS
PAPER_READINESS = 13851_TO_16667_MS
```

The funnel cold query reads 960 run/result pairs for 49 boundaries and projects
five large JSON payloads per pair. Recent projected payload volume is about
67 MiB, averaging 71,268 bytes and peaking at 79,998 bytes per result. The
`online_pipeline_results` heap is 196 MiB, but its total relation size including
TOAST is 6,587 MiB. There are 154,428 live result rows and no relevant dead-row
bloat.

`EXPLAIN ANALYZE` proves the run and unique run-id indexes are used. It returned
960 rows in 25,818.757 ms, with 24,030 shared-buffer hits and 7,425 reads. The
dominant cost is fetching/decompressing and applying JSONB subtraction to the
large payloads, not a missing basic join index. The query is therefore close to
the 30-second database statement timeout under warm diagnostic conditions and
crosses it under normal concurrent production load.

The cache cannot recover from this state: its TTL is 30 seconds, it is populated
only after successful materialization, and no stale value is retained. Once a
cold load times out, every later request performs another cold load and returns
500. The 10-second client refresh then repeatedly exercises the failing path.

## Plan to command/position bridge

Since the selected-winner remediation deployment at 2026-09-26T23:05Z,
production recorded:

```text
SELECTED_WINNERS = 9
COMMANDS_CREATED = 0
POSITIONS_OPENED = 0
READONLY_RUNTIME_NOT_READY = 9_OF_9
ENTRY_FILL_WINDOW_MISSED = 9_OF_9
SELECTION_LATENCY_MS = MIN_34732; AVG_44128; MAX_55242
REMAINING_CAUSAL_WINDOW_AT_SELECTION_MS_AVG = 15873
REMAINING_CAUSAL_WINDOW_AT_CLAIM_MS_AVG = 20143
CLAIM_TO_REFINEMENT_MS_AVG = 51936
```

The operator-control mutation path synchronously calls
`/api/v1/paper/readiness` with a 10-second timeout. That endpoint currently
takes 13.9–16.7 seconds; its runtime subprojection alone takes 13.6–17.2
seconds, while control status, account and reconciliation individually return
in 0.3–0.6 seconds. Runtime observation recomputes the 20-symbol production
approval read and other readiness evidence for every call instead of consuming
a bounded current snapshot. Consequently the operator times out, fails closed
as `READONLY_RUNTIME_NOT_READY`, and the selected plan loses its causal entry
window.

There is a second clock defect in the same gate. The pre-refinement deadline
check receives `execution_as_of_ms` from the approval snapshot as
`claim_attempted_at`, not the actual wall-clock claim time. Under server lag this
timestamp is older than the execution attempt, so the gate can consider a late
attempt in-window. Refinement then uses current wall time, and the plan is
terminalized later as `ENTRY_FILL_WINDOW_MISSED`. Source snapshot time is valid
for data causality but must not be the mutation deadline clock.

## Scope and remediation direction

No strategy, ranking, RR, target, stop, TTL, universe, commission, limits,
control state, database row, service, client file or LIVE setting was changed.

The minimum safe remediation should:

1. Replace the full 960-row/five-JSON regular funnel query with a compact
   normalized current/last-cycle projection; keep historical bulk data behind
   the export path.
2. Use stale-while-revalidate/single-flight caching so a failed refresh cannot
   discard the last valid projection or trigger repeated cold materialization.
3. Add client conditional/incremental refresh and 5xx backoff after the server
   projection is bounded; do not treat a larger timeout as the fix.
4. Remove synchronous heavyweight Readonly readiness computation from command
   ingestion. Consume a timestamped bounded readiness snapshot or equivalent
   lightweight authority that is refreshed independently.
5. Use actual monotonic/wall-clock time for entry-window enforcement, retaining
   approval `as_of_ms` only as source-data causality evidence.
6. Re-run deterministic bridge tests plus a natural post-deploy winner and
   require one command/position or an accurate typed trading rejection.

```text
CURRENT_STAGE = FUNNEL_AND_PAPER_BRIDGE_SERVER_LATENCY_REMEDIATION_REQUIRED
CURRENT_BLOCKER = FUNNEL_SQL_TIMEOUT_AND_SYNCHRONOUS_READONLY_READINESS_TIMEOUT_PREVENT_DESKTOP_REFRESH_AND_PAPER_COMMAND_CREATION
NEXT_ACTION = IMPLEMENT_BOUNDED_FUNNEL_PROJECTION_AND_DECOUPLED_CURRENT_READINESS_THEN_DEPLOY_AND_VALIDATE_A_NATURAL_WINNER
```
