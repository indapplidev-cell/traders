# TRADERS Scalping V2 selected-winner causal execution remediation 02

```text
TASK = TRADERS_SCALPING_V2_SELECTED_WINNER_CAUSAL_EXECUTION_REMEDIATION_02
FINAL_STATUS = PASS
FINAL_VERDICT = SELECTED_WINNER_CAUSAL_EXECUTION_TIMING_DEFECT_PROVEN_FIXED_TESTED_DEPLOYED_AND_SMOKE_VERIFIED
IMPLEMENTATION_COMMIT = b7637ce0ef584b2c604dc34ab26317593e2e1719
ACTIVE_PROFILE = trade-5m-v2
ACTIVE_UNIVERSE = trading-universe-v3; 20_OF_20
MODE = PAPER
LIVE_STATE = DISABLED; live_allowed=false
REAL_BINANCE_ORDER_CALLS = 0
SCHEMA = 0035_scalping_v2_ingestion_policy_contract; UNCHANGED
STRATEGY_CHANGED = NO
RANKING_CHANGED = NO
COMMISSION_POLICY_CHANGED = NO
RR_TARGET_STOP_TTL_WINDOW_CHANGED = NO
UNIVERSE_CHANGED = NO
MAX_LIMITS_CHANGED = NO
LEGACY_15M_CHANGED = NO
NEW_4H_OR_12H_FUNNEL_COLLECTED = NO
```

## A. Evidence boundary and forensic cohort

The named `funnel_2609_092610_586.jsonl` export was not present on disk. The
same production cohort was independently reconstructed from PostgreSQL using
its filename-derived half-open observation interval:

```text
FIRST_OBSERVED_AT >= 2026-09-25T21:26:10.586Z
FIRST_OBSERVED_AT <  2026-09-26T09:26:10.586Z
PLAN_COUNT = 29
DISTINCT_PLAN_BOUNDARIES = 20
SELECTED_PLAN_NOT_CLAIMABLE = 19
LOWER_SELECTOR_RANK = 9
ENTRY_FILL_WINDOW_MISSED = 1
COMMANDS = 0
POSITIONS = 0
```

All 19 selected winners had `selector_reason=READONLY_RUNTIME_NOT_READY`.
Reservation pickup itself was fast: nearest first-canary start after selection
had p50 91.711 ms, p90 137.463 ms, p95 143.322 ms and max 184.113 ms. Every
active reservation subsequently ended
`FAILED_SAFE/CONTINUOUS_RESERVED_APPROVAL_EXPIRED`. The old repeated claim path
overwrote `continuation_claimed_at`; the final persisted values were roughly
four minutes late with `continuation_attempt` 11–14. Therefore:

```text
FAILED_STAGE_OLD_19 = OTHER_PROVEN
ROOT_CAUSE_OLD_19 = READONLY_RUNTIME_NOT_READY_FOLLOWED_BY_CAUSAL_FIRST_1M_ENTRY_DEADLINE_LOSS
PENDING_READ_CLAIM_IDENTITY_DEFECT = NO
```

The exact winner identity and claim path existed. Command creation was blocked
while the read-only runtime was not ready, the worker retried until approval
staleness, and the final generic `SELECTED_PLAN_NOT_CLAIMABLE` hid the causal
deadline loss.

## B. Exact ENAUSDT 09:40Z reconstruction

```text
SYMBOL = ENAUSDT
BOUNDARY = 2026-09-26T09:40:00Z; 1790415600000
SOURCE_RUN_ID = orchestrator:64df1f59b489451db35a700f1578e5cf
PLAN_ID = paper:ENAUSDT:5m:1790415600000:risk:ENAUSDT:5m:1790415600000:strategy:v2:135418494779a1ff6b068a6b2d2e97d11ed42444c883db5ed1b62e00074c5553:2bdc381f04864999:0e2ffcd8381285f4
APPROVAL_ID = paper:risk-approval:v1:934a9dc998e0bdbc5eede6087f0d1160040dcf38b94685d50bee4fbf37ab702f
CANDIDATE_ID = paper:production-approval-candidate:v1:1bcf7a32705fd0badd82fdb98fe70819e26c1d5668feb1c990efa866d2019e4c
OPPORTUNITY_ID = opportunity:8753cadc8766e4d75be64cf0
CONTROL_GENERATION = 15
CONTINUOUS_CYCLE_ID = 5051b7b8-763c-50dc-a92d-d8e3e9d0f16f
```

The old implementation checked the deadline only after refinement and before
reserve, so no canary was reserved for this row. Analysis started at
09:41:10.165727Z (+70.166 s), the plan was created at 09:41:13.526Z, analysis
finished at 09:41:13.579887Z (+73.580 s), and the complete 20-symbol cycle
finished at 09:41:15.214891Z (+75.215 s). Selection occurred at
09:41:27.637302Z (+87.637 s), and the claim succeeded at 09:41:27.657983Z,
20.681 ms after selection but 27.658 s after the first-minute entry deadline.
The row terminalized as `ENTRY_FILL_WINDOW_MISSED` at 09:41:27.733762Z; approval
validity itself extended to 09:44:59.999Z.

The old `refinement_started_at` incorrectly copied `selected_at`. From
`refinement_finished_at - latency`, the actual evaluation began approximately
09:42:10.623Z and completed at 09:42:10.634266Z. The required bar was
09:41:00–09:42:00. At evaluation time the latest stored bar was still
09:40:00–09:41:00; it was not eligible because it closed before selection. The
required 09:41 bar was ingested only at 09:42:17.196560Z. Evaluation was about
10,623 ms past the required close, exceeding the 1m freshness allowance of
10,000 ms, so no bar was chosen. The old generic
`ENTRY_REFINEMENT_MARKET_DATA_STALE` was a downstream mask, not the primary
cause.

```text
ENA_CLAIM_CONTINUATION_REACHED = YES
ENA_CLAIM_RESULT = CLAIMED
ENA_REFINEMENT_REACHED = YES
ENA_LATE_BEFORE_REFINEMENT = YES
ENA_WRONG_SNAPSHOT_SELECTED = NO
ENA_REQUIRED_1M_BAR = 2026-09-26T09:41:00Z..09:42:00Z
ENA_ACTUAL_CHOSEN_1M_BAR = NONE
ENA_1M_FRESHNESS_AGE_MS = APPROX_10623
```

## C. Twenty-symbol transition and latency

Commit `fc9364d39c754dae82b3ae1ef86aa83930e5acb1` expanded the PAPER universe
from 10 to 20 without changing the scheduling model. No current hard-coded
ten-symbol completion guard was found; the exact-20 barrier had already been
added by `b364fc24f805e9f6667ebdfed521d6bd1d46ab55`. The transition is relevant:
doubling cardinality exposed serial scan/poll/maintenance timing, but it did
not introduce a different selector or trading policy.

For the ENA boundary, run completion was +29.596 s for the first symbol,
+32.665 s for the 10th, +33.462 s for the 12th, +70.041 s for the 13th,
+73.580 s for ENA, and +75.215 s for the 20th. All twenty 5m candles were
already ingested by +39.609 s (ENA by +34.588 s). The first scan processed 12;
the latter eight were not yet available when scanned. Before durable waiting
could retry, cycle maintenance, including external commission refresh, could
block, followed by the normal poll interval. This explains the 36-second gap.
Commission rules and timeouts were not changed.

Latency distributions in milliseconds:

| Population / event | p50 | p90 | p95 | max |
|---|---:|---:|---:|---:|
| All 20 winners: first finish | 28808.9 | 47094.9 | 52962.5 | 104676.5 |
| All 20 winners: 10th finish | 35271.9 | 50518.3 | 55535.7 | 115805.7 |
| All 20 winners: median finish | 35747.9 | 50926.6 | 55654.4 | 116131.2 |
| All 20 winners: 20th finish | 40959.6 | 56135.4 | 60256.5 | 130132.5 |
| All 20 winners: complete to selected | 9016.1 | 12116.2 | 12549.8 | 13316.9 |
| All 20 winners: selected to terminal | 265497.8 | 279249.5 | 281834.6 | 282093.0 |
| Old 19: first finish | 27397.8 | 39280.6 | 47094.9 | 50240.7 |
| Old 19: 10th finish | 34931.9 | 46317.6 | 50518.3 | 52363.6 |
| Old 19: median finish | 35031.7 | 46749.5 | 50926.6 | 52471.4 |
| Old 19: 20th finish | 40789.3 | 53702.3 | 56135.4 | 56578.8 |
| Old 19: complete to selected | 9006.8 | 12159.9 | 12590.1 | 13316.9 |
| Old 19: selected to terminal | 265805.2 | 279535.2 | 281848.2 | 282093.0 |

Nineteen of twenty cycles completed the 20th symbol by +60 s; one did not.
Sixteen selections were by +60 s and four were later. The overwritten old JSON
claim timestamps and all refinement terminal timestamps were after +60 s and
must not be interpreted as first-pickup metrics; the canary-start correlation
above proves initial pickup was sub-200 ms.

## D. Remediation

- The orchestrator now schedules a durable waiting 5m boundary on the existing
  5-second freshness retry interval and skips potentially blocking cycle
  maintenance only for that immediate deferred-boundary retry.
- The executor records selector start and exact-run rehydration, uses source
  `as_of_ms` for deterministic claim time, and checks causal first-1m deadline
  both before refinement and at pickup. A late selected winner terminalizes
  immediately as `ENTRY_FILL_WINDOW_MISSED`; an active reservation fails safely
  as `CONTINUOUS_ENTRY_FILL_WINDOW_MISSED`.
- Claim evidence is restart-safe. Replays report `CLAIM_REPLAY` without
  overwriting the first `continuation_claimed_at`; generation mismatch is a
  typed rejection.
- Persisted observability now includes cycle complete, selector start, pending
  selected visibility, read-by-run, rehydration, claim attempt/result/failure,
  true refinement start, required 1m open/close, actual snapshot timestamp,
  freshness age and typed stale/unavailable reasons.
- An older 1m bar may be reported for diagnosis but is never reused as the
  causal entry bar.

No strategy, ranking, commission, RR, target, stop, TTL, causal window,
universe, limit, LIVE, or 15m rule changed.

## E. Deterministic A–J acceptance

| Case | Evidence | Result |
|---|---|---|
| A: exact 20, causal valid winner | PostgreSQL exact-20 E2E: 20 source decisions, 18 natural plans, one winner, 17 lower-rank outcomes, one command, zero duplicate commands | PASS |
| B: selected at +55 s | exact-20 deadline test remains eligible | PASS |
| C: selected at +70 s | immediate typed `ENTRY_FILL_WINDOW_MISSED`, no refinement/command | PASS |
| D: exact required 1m bar | refinement uses the causal bar | PASS |
| E: only older 1m bar | old bar reported, typed wait/unavailable, never reused | PASS |
| F: multiple plans | one selected winner plus 17 deterministic lower ranks | PASS |
| G: restart/replay | exact-run PostgreSQL regression and two-position restart regression | PASS |
| H: concurrent workers | database claim grants one owner | PASS |
| I: expiry race | claimed row is protected; replay preserves first claim timestamp | PASS |
| J: control generation mismatch | exact typed claim rejection | PASS |

## F. Validation

```text
COMPILEALL = PASS
TARGETED_UNIT = 41_PASS; 1_DESELECTED_KNOWN_STALE_MIGRATION_EXPECTATION
BROADER_SELECTED = 2850_PASS; 1_DESELECTED; 7_KNOWN_PREEXISTING_STALE_FIXTURE_FAILURES
POSTGRES_EXACT20_E2E = PASS
POSTGRES_REGRESSION = 4_PASS_IN_66.46_SECONDS
```

The seven broader failures are old retry fixtures that instantiate
`trade-5m-v2` without primary `5m` in `required_timeframes`; they fail in
configuration validation before reaching the changed code. They were not
modified. Isolated test databases/role and the temporary password file were
removed after the run.

## G. Deployment and smoke evidence

Only `online-orchestrator-5m`, `operator-control-api`, and `readonly-api` were
rebuilt and force-recreated with `--no-deps`. All three images/containers expose
the implementation revision
`b7637ce0ef584b2c604dc34ab26317593e2e1719`; both API healthchecks are healthy
and all restart counts are zero. PostgreSQL, market-data, calibration collector
and legacy 15m were not recreated.

```text
READONLY_HEALTH = OK; ready=true; operational=true
PAPER_READINESS = READY
PAPER_CONTROL = CONTINUOUS_ARMED; GENERATION_15; HEALTHY
PAPER_MUTATION = READY
WAL = READY
PITR = READY
ALEMBIC = 0035_scalping_v2_ingestion_policy_contract
UNIVERSE = 20_ACTIVE_OF_20; 120_READY_STREAMS_OF_120
COMMISSION = READY; REAL_ACCOUNT_DATA_TRUE; 20_OF_20; failure_count=0
COMMISSION_LAST_SUCCESS_AT = 2026-09-26T23:06:26.377866Z
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
```

The read-only recovery-worker diagnostic still carries an older internal
`DEGRADED/OperationFailure` payload, while authoritative current WAL and PITR
domains are READY and overall PAPER readiness is READY. This was not introduced
or changed by the task and does not block this PAPER remediation.

## H. Decision and next stage

```text
FINAL_VERDICT = PASS
CURRENT_STAGE = POST_REMEDIATION_NATURAL_PAPER_FUNNEL_OBSERVATION
CURRENT_BLOCKER = NONE_FOR_IMPLEMENTATION_TEST_DEPLOYMENT_OR_SMOKE; LIVE_REMAINS_DISABLED_BY_POLICY
NEXT_ACTION = VALIDATE_THE_NEXT_NATURAL_FUNNEL_COHORT_WITHOUT_FORCING_A_SIGNAL_OR_COLLECTING_A_NEW_4H_OR_12H_WINDOW
```

This result proves and repairs the causal execution defect. It does not claim a
new natural post-deployment trading sample, production profitability, canary,
or 72-hour soak acceptance.
