# Scalping night funnel and cost-aware construction remediation 01

## Verdict

The observed zero-throughput night was caused by an inconsistent construction
contract, not by the configured `1.5` RR threshold alone.  The production
builder stopped at the first causal target with positive net edge; only after
that choice did a late gate require both gross and net RR of 1.5.  It therefore
rejected every one of the 40 candidates entering RR and never considered a
farther target that already existed in the strategy's causal hierarchy.

The builder now preserves the structural invalidation stop, loads the canonical
round-trip cost model before target selection, derives the minimum target from
the production net-PnL equation, and traverses only the existing ordered causal
targets.  It selects the first target that remains structurally valid and has
net RR at least 1.5 after conservative normalization.  It does not synthesize a
target or move a stop.  Absence of such a target is persisted as
`ECONOMIC_GEOMETRY_NOT_FEASIBLE`; the residual RR gate recomputes the same model.

## Authoritative window and data quality

The principal window is the civil night `2026-09-01 00:00:00` through
`08:00:00 Europe/Moscow`, represented as the half-open causal input interval
whose closed boundaries satisfy `boundary > 2026-08-31T21:00:00Z` and
`boundary <= 2026-09-01T05:00:00Z`.

```text
EXPECTED_5M_BOUNDARIES = 96
EXPECTED_SYMBOLS_PER_BOUNDARY = 10
ACTUAL_BOUNDARIES = 96
ACTUAL_CANDIDATES = 960
MISSING_BOUNDARIES = 0
PARTIAL_BOUNDARIES = 0
MISSING_CANDLES = 0
DUPLICATE_CANDLES = 0
DUPLICATE_SYMBOL_ROWS = 0
FUTURE_LEAKAGE_ROWS = 0
```

The fixed observed four-hour slice is `2026-09-01T03:45:00Z` through
`07:45:00Z`: 48 complete boundaries, 480 candidates, and no missing, duplicate,
partial, or future rows.

The secret-free local evidence dataset and complete RR causal table are emitted
by `scripts/diagnose_scalping_night_funnel.py` under the ignored directory
`reports/diagnostics/scalping-night-remediation-01/`.  Historical unknown
quantity, notional, and risk amount values remain null; they were not replaced
with fabricated zeroes.

## Funnel before remediation

| Stage | Input | Pass | Reject | Conversion |
|---|---:|---:|---:|---:|
| Analysis | 960 | 960 | 0 | 100.00% |
| Structural setup | 960 | 57 | 903 | 5.94% |
| Strategy | 57 | 50 | 7 | 87.72% |
| Risk compatibility | 50 | 50 | 0 | 100.00% |
| Geometry | 50 | 42 | 8 | 84.00% |
| Target | 42 | 41 | 1 | 97.62% |
| Costs | 41 | 40 | 1 | 97.56% |
| RR | 40 | 0 | 40 | 0.00% |
| Final pick | 0 | 0 | 0 | n/a |
| Plan PAPER | 0 | 0 | 0 | n/a |

RR rejected 31 rows as low gross RR and 9 as low net RR.  Nine of 40 would
have met the gross threshold, but none met the net threshold.

The fixed four-hour slice independently reproduced the symptom: 480 analysis,
42 setup, 41 strategy/risk, 34 geometry, 31 target, 26 costs, and zero RR pass.

## Night distributions at RR

| Metric | Count | Min | P50 | P90 | Max |
|---|---:|---:|---:|---:|---:|
| stop distance, bps | 50 | 6.3175 | 57.7689 | - | 132.6880 |
| target distance, bps | 41 | 24.0292 | 38.1919 | - | 99.3161 |
| gross RR | 40 | 0.3945 | 1.0598 | 2.6819 | 5.3907 |
| net RR | 40 | 0.0262 | 0.1770 | 0.5555 | 1.0353 |
| modeled round-trip cost, bps | 40 | 27.0406 | 27.8846 | - | 27.9706 |
| gross-minus-net RR drag | 40 | 0.3660 | 0.7575 | 2.3013 | 5.2047 |
| actual target shortfall, bps | 40 | 22.1402 | 87.7088 | - | 156.3252 |
| break-even win rate | 40 | 0.4913 | 0.8496 | - | 0.9745 |

The configured fee inputs were 10 bps per side and slippage inputs 2 bps per
side.  Median spread was 0.8848 bps, median modeled depth impact was effectively
zero, and the canonical safety margin completed the 27.8846 bps median
round-trip total.

## Formula reconstruction

For LONG and SHORT the implementation uses the same signed-distance-normalized
equation:

```text
total_cost = entry_fee + exit_fee + entry_slippage + exit_slippage
             + spread + depth_impact + safety_margin
net_reward = gross_reward - total_cost
net_risk   = gross_risk + total_cost
net_rr     = net_reward / net_risk
minimum_gross_reward = total_cost + required_net_rr * (gross_risk + total_cost)
```

All 40 night RR rows recomputed from persisted inputs.  LONG count was 16 and
SHORT count was 24.  Maximum absolute error was below `5e-9` bps for cost,
reward, and risk and below `4.3e-9` for net RR.  Entry and exit fees, directional
slippage, spread, and depth are each counted once.  Quantity rounding does not
enter this bps ratio; downstream sizing retains the existing authoritative
instrument quantity registry and revalidates the selected plan.

The 1.5 policy was introduced together with explicit gross and net checks.  Git
history does not support the claim that it was silently converted from a gross
threshold.  The policy therefore remains 1.5; its semantics are now explicitly
versioned as net RR.

## Structural setup diagnosis

The low discovery conversion is not an RR artifact.  Of 903 structural
rejections, all lacked a structural trigger and liquidity/level context; 726
also lacked directional context.  Distance to a complete setup was P50 3
missing conditions (min 2, max 3).  Regimes were UNKNOWN 376, FLAT 350, UP 104,
and DOWN 73.  The 57 valid setups were 45 `SCALP_BREAKOUT` and 12
`SCALP_COMPRESSION_BREAK`.  Closed-candle alignment, exact 5m boundaries,
timezones, candle completeness, and future leakage checks passed, so no setup
threshold was weakened.

## Deterministic before/after replay

On the principal night, cost-aware construction found an existing 15m causal
target for 11 candidates.  Opportunity dedup produced 9 projected final picks
and 9 projected PAPER plans.  The remaining causal outcomes were 29 economic
geometry infeasible, 8 structural stops too wide, 1 missing target, and 1
invalid cost geometry.  No target or order was synthesized.

Two independent full-night windows were replayed without parameter changes:

- `2026-08-30T21:00Z..2026-08-31T05:00Z`: before 12 deduplicated plans; after
  12.  The farther target traversal changed construction provenance but did not
  increase the final trade count.
- `2026-08-29T21:00Z..2026-08-30T05:00Z`: before 0; after 0, because all seven
  cost-stage candidates lacked an economically feasible structural target.

This removes the architectural 100% rejection without imposing a target trade
rate or bypassing strategy, risk, portfolio, or opportunity dedup policy.

## Persistence, contracts, and validation

Accepted and rejected diagnostics now retain entry, raw/final structural stop,
selected/considered targets, all cost components, gross/net RR, required RR,
minimum economic target, feasibility, provenance, and geometry/cost/RR/target
model versions inside the durable pipeline result.  Readonly and export expose
those server-authored values; clients do not recompute trading truth.  New
server-authoritative RU/EN reason strings are generated into the Desktop
bootstrap.  Mobile needs no contract mutation because the additions are
backward-compatible downstream-detail keys and server reason codes.

```text
GEOMETRY_VERSION = scalping-cost-aware-geometry-v2
COST_MODEL_VERSION = scalping-round-trip-net-pnl-v2
RR_POLICY_VERSION = scalping-required-net-rr-v2
TARGET_POLICY_VERSION = scalping-causal-cost-aware-target-v2
RUNTIME_PARAMETER_SET = trade-5m-v1-runtime-v1-af11b65b74275bf3
SCHEMA_HEAD = 0020_paper_plan_execution_outcomes
MIGRATION_REQUIRED = NO_JSON_PERSISTENCE_AND_ADDITIVE_READONLY_CONTRACT
UNIT_GEOMETRY = 42 passed
SERVER_FOCUSED = 206 passed, 12 skipped
SECURITY_STATIC = 711 passed
POSTGRES16_E2E = 5 passed
DESKTOP = 1483 passed, 2 skipped, 3029 subtests passed
MOBILE_CLEAN_WORKTREE = testDebugUnitTest PASS
COMPILE = PASS
```

The unbounded repository pytest invocation is not an acceptance suite: it
contains opt-in PostgreSQL groups with intentionally absent DSNs and frozen
historical schema matrices.  It recorded 30,862 passes before those known
environment/stale-matrix failures.  All changed-path, applicable contract,
security, and fresh PostgreSQL E2E suites pass.

## Safety

No real Binance order API was called, no production trading history was
inserted, and no signal was forced.  LIVE remained disabled throughout.
Deployment replaced only Readonly, 5m orchestrator, and the calibration
collector; PostgreSQL, 15m orchestrator, market-data sync, and operator control
were not replaced.  The collector started a new versioned segment and reports
zero errors, zero promotions, zero production trading mutations, and zero
Binance order calls.

At the final production reread, Readonly revision was
`22b66353b18f39ec369b80bcabd4c8e6eb9f3199`, its image was
`sha256:693485a64f19285e8d14b08fc1012efafc13221846fc23811b06588948dc6318`,
the 5m orchestrator image was
`sha256:b0c8da13af68dcbdffc557362bf8568194ab15dac4f967101ec2d50dbf2be4d6`,
and the collector image was
`sha256:c55e6d4f02c45480c6445f2df203edd9a77aa6ab75d38c734f9beb175d8f7615`.
The running orchestrator imported all four v2 model identifiers and parameter
set `trade-5m-v1-runtime-v1-af11b65b74275bf3` from its installed package.

Three natural post-deploy 5m boundaries (`12:30`, `12:35`, and `12:40` UTC)
completed with exact ten-symbol rows, a new singleton owner, no error/restart,
no future bars, and no private/order API use.  None naturally reached geometry,
so no signal was forced; correctness on real candidates is established by the
deterministic production-night and independent-window replays above.  Final
readiness was WAL true, PITR true, current mutation ready, Control ARMED
generation 6, schema 0020, LIVE false, command count 0, and position count 0.
