# Traders exploration v2 and requalification policy 01 — final audit

```text
FINAL_STATUS = PASS
FINAL_VERDICT = EXPLORATION_V2_AND_DURABLE_EMPIRICAL_REQUALIFICATION_IMPLEMENTED_TESTED_DEPLOYED_AND_ENABLED_FOR_TRADE_5M_V2_PAPER_ONLY; NORMAL_NEGATIVE_EV_VETO_AND_LIVE_SAFETY_UNCHANGED
PROJECT_STATE_COMMIT = a8b7863607c2be1ecb5e6913dc1dc13e0fc3df72
CORE_IMPLEMENTATION_COMMIT = 3c54e6ee50b73ba1f0163ab76e3be3352c074b98
RECONCILED_AT_UTC = 2026-09-29T20:05:54Z
MODE = PAPER
ACTIVE_PROFILE = trade-5m-v2
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
```

## A. Starting state and 12h evidence

The preceding production evidence contained 144 observed cycles and 28 RR
candidates. Normal passes and v1 exploration eligibility were both zero. The
best observed candidate net RR was `2.4085`, below the established authority's
dynamic requirement `2.759419282085097`. The established setup authority was
the immutable 20-observation population with 7 wins, 13 losses, empirical EV
`-18.081946112391396 bps`, and expected EV R `-0.5631950991380469`.

Production started this task at Alembic `0035`, 75 PAPER commands, zero
non-PAPER commands, 73 CLOSED positions, and zero v1 exploration commands,
OPEN positions, or CLOSED positions. The earlier v1 lane was enabled but had
collected no production observation.

## B. Exact v1→v2 policy diff

V1 required `candidate_net_rr >= required_dynamic_rr`. V2 does not use the
negative authority's dynamic RR as an exploration eligibility gate. It requires
the unchanged configured `minimum_planned_rr` and all existing non-empirical
geometry, target, cost, commission, freshness, causal, risk, sizing, portfolio,
TTL, and selector gates. The only bypass remains the normal rejection
`SCALPING_EMPIRICAL_EXPECTANCY_REJECTED` caused by an established negative
empirical authority.

## C. Exploration v2 eligibility

The runtime admission label is `PAPER_EXPLORATION_V2`, with policy version
`limited-paper-exploration-v2`. Exact version provenance is persisted through
diagnostics, plan outcome, production approval, command selection, funnel, and
export. A missing or mismatched version fails closed. Normal admission always
takes precedence.

## D. Budget and authority-population key

The budget key remains the shared `authority_population_id`, including the
existing cross-symbol setup fallback. Limits are global concurrent 1, authority
OPEN 1, new exploration commands per cycle 1, authority rolling 24h 16, global
rolling 24h 16, and five minutes after the latest CLOSED probe. V1 and v2 rows
both consume safety budget, while only new v2 CLOSED probes count toward
requalification.

## E. PAPER-only safety

Both admission modes are rejected outside `trade-5m-v2`, outside PAPER, when
LIVE is allowed, or when the explicit flag is false. The existing final
approval, command, order, fill, position, and exit mechanics are reused. No
Binance order path was invoked. Production `live_allowed=false` before and
after deployment.

## F. Recovery state machine

Durable campaign states are `EXPLORATION_RECOVERY_ACTIVE`,
`REQUALIFICATION_PENDING`, and terminal `REQUALIFIED_ACTIVE`, with a preserved
initial generation and active-generation reference. Every new negative active
authority begins a new campaign; confirmation state is not reused.

## G. Recovery rolling window

The authority window is the latest 20 compatible realized CLOSED observations,
ordered causally by close time and position ID. It combines compatible normal
history and v2 probes, excludes v1 exploration, and never deletes or rewrites
older rows. New observations enter and oldest observations leave only the
active projection.

## H. Requalification math

Requalification requires a full 20-observation window, at least eight new v2
CLOSED probes since campaign start, at least three symbols, empirical EV above
zero, and expected EV R above zero. The same conservative empirical estimator,
prior, confidence bound, and payoff semantics used by normal policy are reused.

## I. Two-confirmation logic

Each confirmation must be triggered exactly once by a distinct newly CLOSED v2
position and therefore by a distinct window fingerprint. One passing window
sets confirmation 1 and leaves normal blocked. The next new passing window sets
confirmation 2 and promotes exactly once. A failing intervening window resets
the count to zero; replaying an unchanged window does nothing.

## J. Authority generations/promotion

Alembic `0036_empirical_requalification_authority` adds immutable authority
generations, recovery campaigns, and exactly-once evaluations. A partial unique
index permits only one active generation per authority population, while the
population/window unique key prevents duplicate generations. Promotion
supersedes but retains the old negative generation.

## K. Continuous learning after requalification

After promotion, normal evaluation reads the active generation. Each compatible
realized normal or v2 CLOSED result advances the latest-20 generation without
mutating prior generations. Exploration eligibility naturally stops while the
active authority is positive and normal candidates use the new fingerprint and
statistics.

## L. Negative-again recovery loop

If the continuously updated latest-20 generation becomes negative again, it is
persisted as the new active generation and a new recovery campaign starts with
zero probes and zero confirmations. The earlier terminal campaign and authority
lineage remain queryable.

## M. Durable state/idempotency

Campaign, evaluation, promotion, and active-generation state are PostgreSQL
transactions. Unique keys make restart/replay stable. Unit state-machine and
PostgreSQL E2E assertions proved no duplicate evaluations, generations,
campaigns, or commands and preserved the original realized PnL/timestamps.

## N. Observability

Funnel/API/export now expose v2 eligibility/selection/block reason, authority
generation/state, campaign ID, probe and symbol counts, confirmation count,
window size/EV/expected-EV-R/fingerprint, and requalification status/reason.
Policy version and authority provenance continue into durable outcomes.

## O. Focused tests

The primary regression run passed `1546` tests. Post-audit focused runs passed
`26`, `18`, and the exact schema-startup test. The A–U contract passed: v1
failure reproduction, base RR, non-empirical gate denial, normal priority,
shared budget, one OPEN, cooldown, rolling budget, LIVE block, replay,
latest-20 behavior, minimum probes, symbol diversity, first/second confirmation,
reset, authority switch, normal resume, negative-again loop, history
immutability, and common execution mechanics.

An attempted whole legacy orchestrator test module also exposed seven unrelated
pre-existing references to the removed `trade-5m-v1` profile; the changed
schema-startup contract itself passed and this stale test baseline did not
affect the v2/requalification acceptance.

## P. PostgreSQL E2E

The task-owned PostgreSQL 16 database used a non-superuser `paper_test_`
principal. Migration upgrade, downgrade, and upgrade all passed at the single
head `0036`. Two integration tests passed. The full lifecycle persisted 20 old
normal CLOSED positions, admitted and persisted nine v2 PAPER command/order/
fill/CLOSED lifecycles across three symbols, recorded confirmation 1 at probe 8,
confirmation 2 at probe 9, promoted one active generation, admitted a normal
candidate under it, replayed without duplicates, and verified zero LIVE rows
and no mutation of the original 20 positions.

## Q. Deployment/runtime identities

Implementation was pushed before deployment. A disabled-first rollout applied
Alembic `0036` and rebuilt only the 5m orchestrator, operator-control, and
read-only API. The first attempt proved that two schema capability guards still
ended at `0035`; both services failed closed without data mutation. Commit
`a8b7863607c2be1ecb5e6913dc1dc13e0fc3df72` extended the exact guards to
`0036`, was pushed, rebuilt, and passed health.

```text
ORCHESTRATOR_IMAGE = sha256:b4a425c8c334d0cdacce42859282128a5fc5f34b8a0c3d5323db283445714132
READONLY_IMAGE = sha256:65440431f73ac87d1b961fce31249f2a19d1b2bb35ad2a19d990ada9b2dd7aee
OPERATOR_IMAGE = sha256:96caebe40a82dcf72aa93a3b9bfe3f557430263f05f1ca0d85cba16267e73ada
SOURCE_IDENTITY = a8b7863607c2be1ecb5e6913dc1dc13e0fc3df72
ALEMBIC = 0036_empirical_requalification_authority
```

## R. Production bounded smoke

V2 and requalification were enabled only in the 5m PAPER orchestrator and
PAPER operator. The natural `2026-09-29T20:00:00Z` boundary completed 20/20
runs. No natural eligible v2 probe appeared, no trade was forced, commands
remained 75, non-PAPER commands remained zero, CLOSED positions remained 73,
and all three new tables remained empty. A transient 118/120 market-data view
recovered to 120/120; final health was `OK/CURRENT/operational`, paper readiness
was `READY`, schema ready, control `HEALTHY`, universe v3 exact 20, commission
snapshot `READY` for 20 symbols with real account data, and LIVE false.

`NATURAL_V2_PROBE = NOT_OBSERVED_DURING_BOUNDED_SMOKE`.

## S. Unchanged invariants

Normal empirical policy, negative-EV veto, bootstrap, fallback hierarchy,
target, stop, entry, cost and commission model, risk, sizing, normal selector
ranking, portfolio limits, max one new command per cycle, universe, TTL, exit,
Net PnL Protection, trade-15m-v1, and LIVE policy did not change. Production
history was not mutated. Full rollback was not required; both feature flags are
independent fail-closed switches.

## T. Remaining risk: current cross-symbol setup authority unchanged

The setup-level fallback still shares one authority population across symbols.
V2 deliberately preserves that proven architecture, and its 16-probe budget and
three-symbol diversity therefore also operate on the shared population. This is
the remaining design risk; changing the hierarchy or population identity is out
of scope. The operational next action is passive observation of a natural v2
PAPER OPEN→CLOSED probe and later real recovery evidence, with LIVE disabled.
