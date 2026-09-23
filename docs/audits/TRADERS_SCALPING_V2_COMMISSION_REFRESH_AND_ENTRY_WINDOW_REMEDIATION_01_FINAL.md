# Scalping v2 PAPER commission refresh and entry-window remediation 01

Date: 2026-09-23  
Profile: `trade-5m-v2`  
Mode: PAPER  
LIVE: disabled

## Verdict

`PASS`: the authoritative Binance account-commission source now records a
sanitized durable health state, retries after transient failures, hydrates a
fresh snapshot after restart, and exposes freshness/retry fields to readonly
reporting. The causal entry-window contract was audited and was not weakened.
The observed historical `ENTRY_FILL_WINDOW_MISSED` rows were valid: the plan
was created after the only admissible next 1m candle close, so there was no
technical command-pickup bug to repair.

## Commission authority

The single canonical owner is the continuous 5m orchestrator. It constructs
`BinanceAccountCommissionManager`, performs startup refresh, and calls
`ensure_fresh` once per orchestrator cycle. PAPER cost evaluation reads the
atomically replaced snapshot; it does not use public fee estimates as
authority. The exact authenticated path is Binance Spot
`GET /api/v3/account/commission`, signed with HMAC SHA-256 and an API-key
header. Server time is obtained from `/api/v3/time` and applied to the signed
timestamp. The manager queries all 20 configured symbols and replaces the
snapshot only after every symbol parses successfully.

Configured policy remains unchanged: refresh cadence `3600s`, retry interval
`300s`, maximum snapshot age `86400s`, TAKER entry and TAKER exit, fail-closed,
no stub or static fallback. Snapshot writes remain atomic and mode `0600`.

Before remediation, the production snapshot was fetched at
`2026-09-21T00:52:18Z` and was stale at the task start on 2026-09-23. The
prompt's claimed `2026-09-22T00:50:45Z` timestamp did not match the durable
artifact and is recorded as a prompt/runtime mismatch. A forced authenticated
refresh from the production orchestrator container queried all 20 symbols and
returned `READY`; after the rebuild/restart, startup refresh produced a new
snapshot at `2026-09-23T15:57:54Z`.

The new sidecar status file stores only sanitized metadata:
`source`, account/symbol scope, `status`, `last_attempt_at`,
`last_success_at`, `refresh_failure_count`, typed `last_error_code`,
`next_retry_at`, and snapshot timestamp. Error classes are mapped to
`NETWORK_ERROR`, `TRANSIENT_REFRESH_FAILURE`, `RATE_LIMITED`,
`AUTHENTICATION_FAILURE`, `INVALID_RESPONSE`, or `CLOCK_SKEW`. Secrets,
signatures, headers, and credential contents are never persisted or logged.

## Self-recovery and restart evidence

The deterministic manager tests cover initial READY, valid-cache use during a
transient failure, retry and recovery, fail-closed after TTL, changed symbol
scope, all 20 symbols, status persistence, and restart hydration. The focused
commission suite passes `11` tests. Production after restart reports:

```text
status=READY
active_symbols=20
active_symbols_ready=20
commission_refresh_failure_count=0
commission_ttl_seconds=86400
last_attempt_at=2026-09-23T15:57:54.523363Z
last_success_at=2026-09-23T15:57:54.523363Z
snapshot_age_seconds≈10.6
```

While stale or unavailable, `read_binance_commission_snapshot` remains
fail-closed and the v2 cost gate continues to return
`PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION`. No synthetic fee was added.

## Entry fill window forensic

The implementation contract is `_candidate_entry_fill_window_missed` in
`app/operator_control/production_executor.py`: the next deterministic 1m
fill close is `boundary_closed_at + 60_000ms`; an approval created after that
close cannot be filled causally. The lifecycle worker applies the same rule
to its selected candle. No older candle, future candle, backdated timestamp,
or TTL extension is permitted.

Production PostgreSQL contained `13` v2 rows with terminal reason
`ENTRY_FILL_WINDOW_MISSED` across boundaries
`1788598800000..1790015400000`. Their plan-to-boundary delay was:

```text
count=13; average=89,279.9ms; minimum=67,678ms; maximum=219,474ms
```

Thus every audited row was already later than the admissible next-1m close
before command creation. Refinement and ingestion timestamps are exposed by
the readonly funnel (`refinement.started_at`, `finished_at`, and causal
validity bounds); the evidence does not show a command-pickup race that could
be fixed without lookahead. Conclusion: `HISTORICAL_REASON_VALID=YES`,
`TECHNICAL_DELAY_BUG=NO`, `LOGIC_CHANGED=NO`.

## Validation and deployment

- `tests/engine_paper/test_binance_account_commission.py`: `11 passed`.
- Existing focused lifecycle/ranking group: `38 passed`, with one unrelated
  pre-existing Alembic predecessor assertion failure.
- Production orchestrator rebuilt/recreated as the sole refresh owner.
- Readonly API rebuilt/recreated for the new commission health fields.
- No Alembic migration was needed.
- Production remains `trade-5m-v2`, `trading-universe-v3`, 20 symbols, PAPER,
  LIVE disabled, and zero real Binance order calls.
- Health/readiness/funnel/analysis/universe/positions endpoints remain the
  required readonly surface and were checked after deployment.

Implementation commits: `f61245569bdce7ae742898101ab8515c34d07e23`
(refresh authority) and `54b2cb45297dc181451aed889e0e91d2411c8fa1`
(schema-0035 runtime guard and final audit integration).
