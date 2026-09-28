# Traders Limited PAPER Exploration Lane — Final Audit 01

Reconciled at: `2026-09-28T20:25:58Z`

Implementation commit: `915ffcbacbdcb0ef3dd8225f7525627fb7a7b395`

Scope: `trade-5m-v2`, PAPER only

## A. Starting evidence

The preceding empirical forensic established one shared setup-level authority
population with 20 normal CLOSED observations (7 wins, 13 losses), empirical EV
`-18.081946112391396 bps`, expected EV `-0.5631950991380469 R`, and dynamic
required RR `2.759419282085097`. Attribution, fallback hierarchy, query scope,
and arithmetic were correct. The normal negative-EV veto was intentional, but
made new authoritative evidence unreachable without a separately authorized
policy lane.

No historical observation, PnL, bucket key, or normal policy value was changed.

## B. Architecture — Normal vs Exploration

`NORMAL_EMPIRICAL_ADMISSION` remains the normal authority path. The new
`PAPER_EXPLORATION_ADMISSION` path is a separately labelled information-gathering
lane. It is behind `PAPER_EXPLORATION_ENABLED`, whose code and compose default is
`false`, and is accepted only for `trade-5m-v2` PAPER execution.

Normal candidates are selected first. If any normal eligible candidate exists,
exploration candidates receive `NORMAL_COMMAND_TAKES_PRECEDENCE`; the existing
one-winner selector and `MAX_NEW_COMMANDS_PER_CYCLE = 1` remain unchanged.

## C. Eligibility contract

Exploration can bypass only `SCALPING_EMPIRICAL_EXPECTANCY_REJECTED`. Eligibility
requires all of the following:

- explicit feature enablement, `trade-5m-v2`, and PAPER mode;
- established empirical authority with negative empirical EV;
- normal rejection caused only by the empirical negative-EV veto;
- all earlier structural, strategy, risk, portfolio, geometry, target, cost,
  freshness, commission, causal-window, and refinement gates already passed;
- candidate net RR greater than or equal to the authority's current dynamic RR;
- stable authority population identity and observation-set fingerprint.

Any other reject, insufficient authority, missing provenance, lower RR, disabled
flag, wrong profile, or non-PAPER mode fails closed.

## D. Budget contract

The server-side constants are:

```text
MAX_CONCURRENT_EXPLORATION_POSITIONS_GLOBAL = 1
MAX_OPEN_EXPLORATION_PER_AUTHORITY_POPULATION = 1
MAX_NEW_EXPLORATION_COMMANDS_PER_CYCLE = 1
MAX_EXPLORATION_PROBES_PER_AUTHORITY_POPULATION_ROLLING_24H = 2
MAX_EXPLORATION_PROBES_GLOBAL_ROLLING_24H = 2
EXPLORATION_COOLDOWN_AFTER_CLOSED_HOURS = 6
NEXT_PROBE_REQUIRES_PREVIOUS_PROBE = CLOSED
NEXT_PROBE_REQUIRES_RECOVERY_EVIDENCE_PERSISTED = YES
```

The key is a semantic `AUTHORITY_POPULATION_ID`, not symbol. It contains the
selected hierarchy level and dimensions plus parameter-set/config identity.
Cross-symbol setup fallback therefore shares one budget. Budget state is rebuilt
from durable plan → command → entry order → position rows after restart.

## E. Selector behavior

No ranking algorithm was added. Permitted exploration candidates are passed to
the existing deterministic production eligible-approval selector. At most one
winner is returned; lower ranked candidates retain normal `NOT_SELECTED`
semantics. Budget-blocked candidates preserve `exploration_eligible = true` and
record the exact block reason without becoming normal empirical PASS.

## F. PAPER-only safety

Three independent boundaries fail closed:

1. strategy eligibility accepts only PAPER and `trade-5m-v2`;
2. final approval rejects exploration unless the explicit flag and PAPER profile
   contract are satisfied;
3. production approval/execution requires the flag, valid exploration
   provenance, PAPER execution, and `live_allowed = false`.

The bounded production evidence contained 75 PAPER commands and zero non-PAPER
commands. Readiness reported `live_allowed = false`. No real Binance order call
was made.

## G. Trading-mechanics equivalence

Exploration changes only admission/provenance. It uses the same final approval,
entry refinement, command ingestion, simulated order/fill, position accounting,
target, stop, fees, spread/slippage, adverse reserve, risk sizing, portfolio,
intratrade monitoring, exit decision, and Net PnL Protection paths. No
exploration-specific target, stop, sizing, TTL, cost, or exit branch exists.

## H. Durable provenance

Existing extensible `paper_context` and plan outcome `refinement_details` carry
the admission mode, deterministic exploration ID, policy version, authority
population/bucket/fingerprint, authority sample/wins/losses/EV/dynamic-RR before
entry, normal reject, candidate RR, eligibility, selection/rank/block reason,
budget snapshot, and cooldown. Existing relational IDs link that outcome to the
pipeline run, command, entry order, position, fills, timestamps, exit reason,
fees, and realized PnL. No schema migration was necessary.

Funnel/export keeps `normal_admission = REJECTED` and exposes the independent
exploration decision. Final selection fields come from the durable lifecycle
outcome rather than the earlier strategy snapshot.

## I. Recovery evidence

`PaperExplorationStore.recovery_evidence()` projects a durable cohort per
authority population from real CLOSED PAPER positions: count, wins, losses,
breakeven, average win/loss net bps, EV net bps, first probe, and last probe.
Open/unresolved commands cannot produce recovery evidence and block another
probe.

## J. Normal authority isolation

The authoritative normal statistics source explicitly excludes rows whose
entry admission mode is `PAPER_EXPLORATION_ADMISSION`. Historical rows without
an admission mode preserve legacy/normal semantics. The isolated PostgreSQL
test seeded 20 normal CLOSED observations plus one exploration CLOSED position;
normal authority remained exactly 20 observations and 7 wins while recovery
evidence contained exactly the exploration position. Automatic requalification
does not exist.

## K. Tests

```text
PY_COMPILE = PASS
FOCUSED_EXPLORATION_AND_EXPORT = 23 PASS
ISOLATED_POSTGRESQL_E2E = 1 PASS; 1 ALEMBIC DEPRECATION WARNING
EXPANDED_AFFECTED_RUN = 1525 PASS; TASK_OWNED_EXPORT_ASSERTION_FIXED_AND_REVALIDATED
KNOWN_UNRELATED_BASELINE = DEFAULT_POLL_SECONDS ASSERTS 5 WHILE PROVEN CURRENT VALUE IS 0.5
```

Tests cover sole-blocker admission, other rejects, RR floor, normal priority,
cross-symbol shared population, one-open cap, deterministic cooldown, authority
and global rolling caps, restart state, LIVE rejection, mechanics reuse,
recovery evidence, normal authority isolation, and duplicate command count.

The isolated PostgreSQL 16 database used a test-only non-superuser principal,
upgraded to the single Alembic head
`0035_scalping_v2_ingestion_policy_contract`. It proved one PAPER command in the
exploration lifecycle graph, one CLOSED position/recovery row, unchanged normal
authority, and no duplicate command.

## L. Deployment

The implementation commit was pushed before deployment. Affected runtime images
were rebuilt and recreated. The first rollout explicitly used
`PAPER_EXPLORATION_ENABLED=false`; both orchestrator and operator-control read
`false`, and health/readiness checks passed. The second rollout recreated only
the `trade-5m-v2` PAPER orchestrator and PAPER operator-control with the flag
`true`. Read-only remained unflagged, 15m was untouched, and LIVE remained
disabled.

All three deployed services reported source identity
`915ffcbacbdcb0ef3dd8225f7525627fb7a7b395`.

## M. Production smoke

Post-enable acceptance:

```text
HEALTH = OK; OPERATIONAL
READINESS = READY; CONTINUOUS_ARMED
COMMISSION = READY 20/20; COST_MODEL_READY
UNIVERSE = trading-universe-v3; EXACT 20; STREAMS 120/120
LIVE_ALLOWED = false
PAPER_EXPLORATION_ENABLED = true in 5m orchestrator and PAPER operator only
ALEMBIC = 0035_scalping_v2_ingestion_policy_contract
```

A fresh 20-symbol cycle completed after enablement. It produced one normal
empirical rejection but zero exploration-eligible candidates, zero exploration
selections, zero new exploration commands, and zero non-PAPER commands. The
required bounded result is therefore:

`NATURAL_EXPLORATION_PROBE = NOT_OBSERVED_DURING_BOUNDED_SMOKE`.

No trade was forced.

## N. Invariants

Normal negative-EV veto, bootstrap policy, fallback hierarchy, required sample,
priors, confidence, minimum/static RR behavior, cost/EV thresholds, target,
stop, entry, TTL, commission, spread/slippage, risk, sizing, portfolio limits,
normal ranking, max commands, universe membership, exit policy, Net PnL
Protection, trade-15m-v1, and LIVE policy are unchanged. Production history was
not mutated.

Rollback is configuration-only: set `PAPER_EXPLORATION_ENABLED=false` and
recreate the 5m orchestrator and operator-control. No schema rollback is needed.

## O. Next policy boundary

```text
AUTO_REQUALIFICATION = NOT_IMPLEMENTED
REQUALIFICATION_POLICY = SEPARATE_FUTURE_DECISION
```

The next stage is passive observation of a naturally eligible, budget-permitted
probe and its real PAPER OPEN → CLOSED lifecycle. Any rule for converting
recovery evidence into normal authority is outside this task and requires a
separate explicit policy decision.

## Final verdict

`FINAL_STATUS = PASS`

`FINAL_VERDICT = LIMITED_PAPER_EXPLORATION_LANE_IMPLEMENTED_TESTED_DEPLOYED_AND_ENABLED_FOR_TRADE_5M_V2_PAPER_ONLY; NORMAL_EMPIRICAL_AUTHORITY_AND_LIVE_SAFETY_UNCHANGED`
