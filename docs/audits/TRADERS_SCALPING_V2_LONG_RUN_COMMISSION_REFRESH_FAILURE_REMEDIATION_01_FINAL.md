# TRADERS Scalping v2 PAPER long-run commission refresh remediation

Date: 2026-09-25

Scope: `trade-5m-v2`, `trading-universe-v3` (20 symbols), PAPER only. LIVE remained disabled. No order-placement endpoint was invoked.

## Before

The supplied 12-hour evidence window was approximately `2026-09-25 03:00Z` through `14:55Z`: 144 completed 5m cycles, 2,880 rows, and 20 symbols per cycle. All approximately 61 cost-stage evaluations were `PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION`, with `fee_source_status=SNAPSHOT_STALE`, `cost_model_status=NOT_READY`, and `fee_source=FEE_SOURCE_NOT_READY`.

The canonical mounted snapshot was fetched at `2026-09-24T01:11:58.937841Z` for 20 symbols. At the forensic capture (`2026-09-25T15:20:15Z`) the sidecar was `FEE_SOURCE_NOT_READY`; `last_attempt_at=2026-09-25T15:19:43.207510Z`, `last_success_at=2026-09-24T01:11:58.937841Z`, `next_retry_at=2026-09-25T15:24:43.207510Z`, `last_error_code=INVALID_RESPONSE`, and `refresh_failure_count=434`. The snapshot age was approximately 38 hours, beyond the unchanged 86,400-second TTL. The sidecar did not persist `last_check_at`.

Runtime evidence showed one continuous 5m orchestrator, one writable commission mount, and one snapshot/status pair shared read-only with the readonly API. The owner was being called; the failure was during an atomic 20-symbol authenticated refresh. A direct bounded authenticated request from the owner container parsed all 20 configured symbols successfully.

## Root cause

`ROOT_CAUSE_1 = app.engine_paper.binance_account_commission.BinanceAccountCommissionManager.ensure_fresh` caught the whole atomic refresh operation and fail-closed on any transient/invalid response. The 20-symbol transaction therefore retained the old snapshot and repeated a complete refresh attempt every retry interval; no partial snapshot was allowed.

`ROOT_CAUSE_2 = BinanceAccountCommissionManager` kept `_last_failed`, `_last_attempt`, failure count, and error code only in process memory. On restart, the sidecar was not hydrated, so retry eligibility and failure context were reconstructed incorrectly.

`ROOT_CAUSE_3 = BinanceAccountCommissionManager._write_status` used the current check time as a fallback for `last_attempt_at`. A cache hit could therefore be reported as an authenticated refresh attempt, obscuring the real long-run schedule and making forensic timestamps unreliable.

`ROOT_CAUSE_PATH_OR_OWNER_MISMATCH = NONE_PROVEN`. The orchestrator writer, manager, cost-model reader, readonly projection, and health artifacts use the same bind-mounted `production_control/commission` directory. Exactly one process owns writes: the continuous 5m orchestrator.

`ROOT_CAUSE_TELEMETRY = last_check_at was absent and retry state was not restart-safe; status could not distinguish a cache check from a real authenticated attempt.`

## Why previous remediation was insufficient

Earlier tests covered one successful refresh, in-process transient recovery, TTL fail-closed behavior, and a fresh restart hydration. They did not persist and rehydrate the failed-attempt clock, retry deadline, failure count, or error code, and they did not assert that cache reads leave `last_attempt_at` unchanged. Thus the short deterministic tests passed while a long-running process accumulated repeated atomic refresh failures and stale authority without restart-safe state or precise telemetry.

## Fix

- Persist `last_check_at` separately from `last_attempt_at`.
- Keep `last_attempt_at` null until a real authenticated refresh begins; cache hits never rewrite it.
- Hydrate `last_attempt_at`, `last_success_at`, retry state, failure count, and typed error code from the status sidecar on manager construction.
- Keep the existing single orchestrator owner, 3600-second refresh cadence, 300-second retry interval, 86,400-second TTL, authenticated Binance Spot account commission endpoint, TAKER semantics, and atomic 20-symbol replacement.
- Expose commission freshness and cost-model readiness through readonly PAPER readiness.
- Make the no-environment local status reader fail closed instead of raising on an empty path.

No strategy, selector, continuation, RR, target, stop, trade-plan TTL, entry window, universe, or trade-frequency policy changed.

## Tests

- `tests/engine_paper/test_binance_account_commission.py`: 13 passed, including cache-hit attempt semantics and restart retry recovery.
- `tests/server_api/test_trading_funnel.py` plus commission tests: 45 passed.
- `tests/readonly_production_runtime_observation` and readonly contract suite: 1,848 passed; one pre-existing static-policy failure remains because the existing `server_api.trading_funnel` contains the forbidden `binance` token.
- `python -m compileall -q app/server_api app/engine_paper` passed.

The deterministic matrix covers fresh startup/cache, hourly due refresh, repeated 5m checks without refresh storm, transient failure with fresh cache, retry recovery, repeated failures, stale fail-closed, recovery after stale, restart with fresh/stale state, status sidecar reconstruction, canonical path, and atomic all-symbol parsing.

## Production proof

Before deployment the snapshot was stale (`2026-09-24T01:11:58.937841Z`) with `FEE_SOURCE_NOT_READY`, 434 failures, and a retry scheduled. After the canonical owner was recreated, an authenticated 20-symbol refresh succeeded at `2026-09-25T15:31:24.312396Z`; snapshot and `last_success_at` advanced together, `next_retry_at=null`, and failure count reset to zero. A subsequent automatic cycle at `2026-09-25T15:37:35.984420Z` updated `last_check_at` while preserving the same `last_attempt_at`, proving a cache check rather than a fabricated attempt.

Readonly `/api/v1/paper/readiness` returned `READY` with `commission_status=READY`, `commission_symbols_ready=20`, `commission_symbols_expected=20`, `cost_model_ready=true`, fresh snapshot age, and `live_allowed=false`. Authenticated source remained `BINANCE_ACCOUNT_COMMISSION_SNAPSHOT`; no public estimate or synthetic fallback was used.

## Safety

```text
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
```

## Final invariants

```text
ROOT_CAUSE_PROVEN = YES
SINGLE_CANONICAL_REFRESH_OWNER = YES
AUTOMATIC_REFRESH_SCHEDULING = PASS
AUTOMATIC_RETRY_AFTER_FAILURE = PASS
RECOVERY_FROM_STALE = PASS
RESTART_WITH_FRESH_SNAPSHOT = PASS
RESTART_WITH_STALE_SNAPSHOT = PASS
LAST_ATTEMPT_SEMANTICS = REAL_REFRESH_ONLY
20_SYMBOL_ATOMIC_REFRESH = PASS
STALE_SNAPSHOT_USED_AS_AUTHORITY = NO
SYNTHETIC_FEE_FALLBACK = NO
COST_MODEL_FAIL_CLOSED_WHEN_STALE = YES
COST_MODEL_READY_WHEN_FRESH = YES
PRODUCTION_SNAPSHOT_AFTER = FRESH
PRODUCTION_COMMISSION_STATUS_AFTER = READY
NEW_4H_FUNNEL_COLLECTED = NO
NEW_12H_FUNNEL_COLLECTED = NO
PAPER_PLAN_TO_COMMAND_VALIDATION_PERFORMED = NO
```

`STATUS_AS_OF_COMMIT = 22b1df4a12316da96340e2f22427c53b481e17a9` (implementation and readonly contract). Orchestrator deployment source is `9a771c42a45684eb694e8a7f0a4b95218b96ae90`.
