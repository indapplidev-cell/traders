# Binance account commission timestamp recovery — bounded PAPER acceptance

Date: 2026-10-10 UTC. Scope: `trade-5m-v2` PAPER commission authority only.

## Before

- The production 5m orchestrator had been running since 2026-10-06 19:54 UTC.
- At 2026-10-10 05:47 UTC the shared commission status was `FEE_SOURCE_NOT_READY`: 0/20 symbols ready, last success 2026-10-06 21:54:50 UTC, 883 consecutive refresh failures, last error `INVALID_RESPONSE`.
- A separate, read-only authenticated commission probe from the same container fetched and parsed all 20 active symbols successfully. This ruled out a persistent credential, symbol-list, or response-shape failure at probe time, but the old status did not retain Binance's numeric error code. The exact historical `INVALID_RESPONSE` cause is therefore **unproven**.
- The long-lived client cached the Binance server-time offset indefinitely. A timestamp rejection (`-1021`) was not retried after re-synchronization.

## Change

Implementation commit: `a429fe0cd85c04e72ae5a6170488e4715ab19a7a`.

- On Binance `-1021` from the authenticated **commission GET**, clear the cached offset, fetch server time again, re-sign, and retry exactly once. A second rejection fails closed as `TIMESTAMP_OUT_OF_RANGE`.
- Preserve the previous handling of authentication, rate-limit, network, and other invalid-response failures. No order endpoint is called by this code.
- Persist only the failed active symbol and Binance's integer error code in the sanitized status sidecar and readonly Funnel commission projection. Never persist the response body, API key, signature, or signed URL.
- Preserve all-20-symbol atomic snapshot replacement, 3600-second refresh cadence, 300-second retry, 86400-second TTL, and stale-snapshot fail-closed behavior. No strategy, risk, selector, stop/target, LIVE, or trading config changes.

## Validation

- Focused commission and Funnel tests: 50 passed. Additional execution-readiness tests: 16 passed. Diff whitespace check passed.
- Regression tests cover one-time re-synchronization and new signature, repeated `-1021` fail-closed, non-time 4xx without retry, sanitized persisted diagnostics, and restart hydration.
- Orchestrator and readonly API images were built with the full implementation SHA as `org.opencontainers.image.revision`, then only these two services were recreated.
- On startup, the canonical orchestrator refreshed the real account commission snapshot atomically: `READY`, 20/20 symbols, last success 2026-10-10 06:01:13 UTC, failure count 0. The next startup cache check retained the successful attempt timestamp.
- Readonly Funnel reported commission `READY`/20, a complete current 5m cycle with 20/20 processed symbols, and no PAPER plan for that cycle because all 20 had `NO_STRUCTURAL_SETUP`. Readonly health subsequently reported `OK`, `CURRENT`, operational/ready true. Both replaced containers had restart count 0 at this check.
- PostgreSQL Alembic remained `0037_continuous_two_lifecycle_slots`. LIVE remained disabled. No real Binance order endpoints were called.

## Limits and next gate

The fresh snapshot after recreation proves recovery, **not** that the historical failure was necessarily `-1021`: recreation itself starts a new client with a fresh clock offset. The new diagnostic fields make any repeated failure attributable without exposing secrets. This is bounded recovery acceptance, not a 24-hour commission soak or evidence of a natural PAPER plan-to-position path. The current primary funnel blocker remains structural setup formation; stop geometry is the next proven downstream bottleneck. Any further correction requires a new concrete proposal and user approval before edits.
