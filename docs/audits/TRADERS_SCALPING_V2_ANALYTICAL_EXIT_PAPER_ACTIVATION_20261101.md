# Scalping v2 analytical exit — PAPER activation

## Verdict

`PASS_DEPLOYED_AUTHORITATIVE_PAPER`

The continuous closed-candle analytical exit introduced by the preceding
SHADOW deployment is now authoritative for PAPER positions.  The runtime keeps
LIVE disabled and cannot route this exit through a LIVE execution mode.

## Activated behavior

- `exit_policy.analytical_exit.mode = PAPER` in the mounted runtime policy.
- The packaged/default policy is also `PAPER`, preventing an omitted legacy
  YAML field from silently reverting a deployment to SHADOW.
- Every eligible open Scalping v2 PAPER position continues to be evaluated on
  each causally closed 1m boundary with the last causally closed 5m context.
- `ANALYTICAL_EXIT`, `STRONG_REVERSAL_EXIT`, and
  `PROFIT_PROTECTION_EXIT` now create a PAPER-only safety directive and enter
  the existing idempotent exit/close lifecycle.
- Stop-Loss and Take-Profit retain priority on the same candle, including the
  conservative stop-first conflict rule.
- Missing, incomplete, duplicate, gapped, or future candle data remains
  fail-closed for analytical exit; ordinary SL/TP and maximum hold protection
  remain available.

## Safety boundaries

- The downstream directive constructor rejects every mode except
  `ExecutionMode.PAPER`.
- Runtime health after deployment: `mode=PAPER`, `live_allowed=false`,
  `mutation_enabled=true`, worker active, production database ready.
- Control state: `CONTINUOUS_ARMED`, generation `20`, commands used `0`.
- Active-session open/CLOSING positions at verification: `0`.
- Commands with a non-PAPER mode in the production PAPER database: `0`.
- LIVE was not enabled; real Binance order calls caused by this task: `0`.

## Validation

- Focused config, analysis, lifecycle and protection suite: `43 passed`.
- Broader selected suite: `319 passed`; `23` PostgreSQL integration cases did
  not start because `PAPER_TEST_DATABASE_URL` was not configured.  The
  production database was deliberately not repurposed as a test database.
- Application package compilation: PASS.
- Docker image build: PASS.
- Operator container health: `healthy`.
- Runtime revision:
  `94580317ef5059d03aaa893fac0978cd80bf6c12`.
- Runtime image:
  `sha256:18bbbd3295ad48ad8d07e1fc929a857a1dd8693773d8272197c43d80c40fc73a`.
- Worker heartbeat advanced from execution tick `25` to `26` after restart.
- Local implementation HEAD and GitHub branch HEAD matched at activation.

## Evidence boundary

No Scalping v2 position was open at activation, so this task cannot honestly
claim a naturally observed analytical close or post-activation PnL result.
This is not a runtime blocker: the authoritative branch is active and will act
on the next naturally opened PAPER position.  No synthetic command, fill, or
position was inserted into the production PAPER database merely to manufacture
evidence.

Statistical profitability targets (Win Rate above 50%, Profit Factor at least
1.20, and positive net expectancy) remain measurement goals, not facts proven
by activation.

