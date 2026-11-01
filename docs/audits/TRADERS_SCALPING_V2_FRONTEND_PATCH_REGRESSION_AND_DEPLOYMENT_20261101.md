# Scalping v2 frontend/patch regression and deployment report

## 1. Outcome

Status: **PASS_DEPLOYED_WITH_KNOWN_UNRELATED_CLIENT_BASELINE_FAILURES**.

The desktop funnel patch, Android client, fast 20-symbol server analysis, continuous closed-candle monitoring, and authoritative PAPER analytical exits were revalidated together. A server-side concurrency regression found during this verification was repaired and deployed before this report was finalized.

The clean natural 5-minute boundary at `2026-11-01T04:55:00Z` processed all 20 symbols. First analysis started after `3743.4 ms`; the last symbol finished after `8877.4 ms`; per-symbol analysis duration p95 was `2955.0 ms`. This satisfies the agreed hard maximum of 10 seconds and is materially below the historical 49–76 second delay.

LIVE remains disabled. No real Binance order path was enabled or called. The analytical exit mode is authoritative for PAPER only.

## 2. Scope and safety invariants

- Server repository: `traders-ml`, branch `feature/engine-platform`.
- Desktop repository: `traders-client`, branch `main`.
- Android repository: `traders-mobile`, branch `main`.
- Active profile: `trade-5m-v2`.
- Active accounting session: `TRADERS_PAPER_SESSION_02`.
- PAPER initial/current balance at verification: `1000 USDT / 1000 USDT`.
- PAPER control: `CONTINUOUS_ARMED`, generation `20`.
- Analytical exit mode loaded by the deployed operator: `PAPER`.
- LIVE readiness domain: `BLOCKED / LIVE_DISABLED`.
- All persisted execution commands are constrained to `mode=PAPER`.
- Existing user-owned deletions, the pre-existing `online_trader.md` edit, and untracked forensic reports were not staged, reverted, or committed.

## 3. Regression discovered and repaired

The earlier full-universe concurrency change increased symbol workers from 8 to 20 and allowed concurrent `mark_running`/`finish` persistence calls through one pinned profile-owner SQLAlchemy session. The analytical computation itself was safe to parallelize, but concurrent mutation of the same session was not. Runtime evidence was a growing set of rows stuck in `RUNNING`/`CHECKING_FRESHNESS` and degraded boundary latency.

The final implementation:

1. bounds symbol computation to 8 workers, matching the deployed host capacity;
2. keeps independent symbol analysis parallel;
3. serializes only profile-owner persistence through the existing result-store lock;
4. preserves causal ordering and the single-owner database contract;
5. refreshes PostgreSQL planner statistics for the large runtime tables with read/write-neutral `ANALYZE`.

Commits:

- `2d350ba` — `perf(orchestrator): bound symbol workers to host capacity`;
- `488abffdcd303ed662cdade2652fac59515fc421` — `fix(orchestrator): serialize profile-owner persistence`.

## 4. Runtime latency evidence

Clean boundary: `closed_until_ms=1793508900000` (`2026-11-01T04:55:00Z`).

| Metric | Result | Gate |
|---|---:|---:|
| Symbols completed | 20/20 | 20/20 |
| First analysis start | 3743.4 ms | informational |
| Full-universe finish | 8877.4 ms | <= 10000 ms |
| Per-symbol duration p95 | 2955.0 ms | <= 5000 ms |
| Per-symbol maximum duration | 3220 ms | <= 5000 ms |
| Stuck active rows after recovery | 0 | 0 |

The first eight tasks began around 3.74–3.79 seconds after the candle boundary. The remaining tasks began around 5.61–5.75 seconds as bounded worker capacity became available. The final result completed at 8.88 seconds. This proves the processing path is no longer delayed by the removed 15-second wait or by serial processing of all 20 symbols.

No natural Session 02 trade signal occurred during this verification. Therefore signal-to-open and analytical-exit-to-close latency for a real newly opened PAPER position remains awaiting a natural observation; it was not fabricated with a synthetic production mutation.

## 5. Continuous analysis and exit authority

The deployed operator loads `SCALPING_V2.exit_policy.analytical_exit.mode=PAPER`.

For every open Scalping v2 PAPER position, the lifecycle accepts closed 1-minute candle events and combines them with the last causally closed 5-minute context. It computes and persists `ExitEvidenceV2`, including technical, graphical, volume/momentum, and holding-economics components. Confirmed analytical exit, strong reversal, and profit-protection decisions can authoritatively close PAPER positions. Stop-Loss and Take-Profit retain higher priority, and idempotency prevents duplicate close commands.

At reconciliation there were no open Session 02 positions, so the absence of new hold/exit evidence is expected rather than a disabled worker symptom.

## 6. Server validation

- Focused orchestration and latency regression scope: `71 passed` after the final persistence fix.
- Broader relevant server scope: `122 passed`.
- A separate legacy parameterization scope produced `18 passed, 5 skipped, 7 failed`; all seven failures reference removed `trade-5m-v1` fixtures and are not caused by this change.
- Readonly health: HTTP 200, `operational=true`, `ready=true`, online orchestrator `OK`.
- PAPER readiness: HTTP 200, `status=READY`, schema `0040_plan_outcome_session_boundary`, mutation ready, `CONTINUOUS_ARMED`, LIVE disabled.
- PAPER reconciliation: HTTP 200, `HEALTHY`.
- PAPER account: Session 02, 1000 USDT balance, no open positions, no new natural trades.

Deployed orchestrator runtime revision: `488abffdcd303ed662cdade2652fac59515fc421`.

## 7. Desktop client validation

The desktop patch changes only read-only funnel ordering: candidates with a positive status, eligibility, and lower selector rank are shown first. It does not mutate the trading database, create commands, or change server-side strategy decisions.

- Changed-file focused tests: `17 passed`.
- Python compile validation: passed.
- Full regression: `1526 passed, 2 skipped, 3030 subtests, 8 failed`.

The eight failures are known environment or stale-baseline issues outside the modified files: missing/corrupt local Tk resources, stale i18n/detail and source-shape expectations, and PAPER GUI tests whose asynchronous mocks no longer match the current client control contract. No failure points to funnel ordering or server trading behavior.

Desktop commits pushed to GitHub:

- `f835dca648fc98abbbc22c0c7643567b0179903b` — actionable funnel ordering;
- `a8f04bcc0c1b830df98de47b64f1dadba30c37a9` — client validation reconciliation.

## 8. Android validation

With `JAVA_HOME=C:\Program Files\Java\jdk-24`:

```text
gradlew testDebugUnitTest assembleDebug lintDebug --no-daemon
BUILD SUCCESSFUL
49 actionable tasks
```

The Android repository has no task-owned source changes. It has no configured upstream branch, so there was nothing to push from this repository.

## 9. Deployment and Git reconciliation

Only the `online-orchestrator-5m` service was rebuilt and recreated. The deployed image label resolves to server revision `488abffdcd303ed662cdade2652fac59515fc421`; the service remained running after the clean boundary. The operator, market-data, PostgreSQL, and readonly services were not unnecessarily restarted.

The server implementation commits and desktop commits are pushed to their configured upstream branches. Documentation commits are created separately so that project-state reconciliation remains reviewable and user-owned dirty files remain excluded.

## 10. Final verdict

The frontend patches did not break the trading path. The verification did expose a server persistence-concurrency regression, which was fixed before deployment. The current deployed system:

- analyzes all 20 symbols within the 10-second maximum on the clean observed boundary;
- remains event-driven for closed 1-minute candle monitoring;
- keeps continuous 1m/5m analytical exits authoritative in PAPER;
- keeps the 1000 USDT Session 02 accounting boundary;
- keeps LIVE disabled and real exchange orders at zero;
- has no newly observed regression attributable to the desktop or Android clients.

The remaining evidence gap is natural rather than technical: Session 02 still has no natural trade, so the first real PAPER signal-to-open and analytical-exit-to-close timing must be measured when such a trade occurs.
