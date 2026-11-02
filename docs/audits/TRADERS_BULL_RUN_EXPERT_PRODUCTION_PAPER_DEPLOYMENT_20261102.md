# Bull-run expert calibration — production PAPER deployment

## Verdict

`PASS_PRODUCTION_PAPER_DEPLOYMENT_WITH_NATURAL_BOUNDARY_CANARY`.

The independently verified LONG rubric and its October 2026 calibration are
integrated into the production code path, configured in the server-owned YAML,
and deployed to the production PAPER orchestrator and lifecycle operator. LIVE
remains disabled and no Binance order API was enabled or invoked by this task.

The historical result `100/140 (71.43%)` is event-conditioned bull-run coverage,
not a claim of a 71.43% whole-market win rate. The production deployment still
requires forward PAPER observation and the untouched November holdout.

## Deployed calibration

| Control | Value |
|---|---:|
| Calibration | `bull-run-expert-october-2026-v1` |
| Entry threshold | `50` |
| Entry weights | structure `8`, context `22`, momentum `14`, volume `2`, entry quality `22`, liquidity `22`, confirmation `10` |
| Exit weights | graphical `5`, technical `11`, momentum/volume `43`, holding economics `41` |
| Exit thresholds | at-risk `40`, exit `60`, strong reversal `75` |
| Minimum protected net profit | `+8 bps` after modeled executable costs |
| Scope | LONG only; closed 1m/5m OHLCV; PAPER only |

The runtime computes EMA, SMA, MACD, RSI, ATR, ADX, Bollinger, VWAP, volume,
structure, breakout/retest, candle confirmation and 1m/5m alignment directly
from closed candles. It does not read bull-run labels, future extrema or the
project's aggregate verdict. Existing hard data-quality, future-bar,
invalidation, geometry, economics, risk and portfolio gates remain active.

## Code and configuration

- Implementation commit: `efab0e6766b6ea1e134a70c8814535af85a1f1d3`.
- LONG-direction safety fix and final source commit:
  `9e862a3deaac7191eb26032e2dd2b75e7c025301`.
- Server YAML SHA-256:
  `de31f94646bec1b1b0f3920a77942e9e72f7e338a244c68d2e1aa14ead7a7839`.
- Runtime semantic trade-parameter hash:
  `a9e4000e51d69eb5ae3c69b3b9c6e2a4559b13295c03916c221bdf1c25bbf4ea`.
- Active set: `scalping-v2-set-2`, version `scalping-v2-set-2-v2`.
- Alembic: `0040_plan_outcome_session_boundary`; unchanged.

## Tests

- 53 focused tests passed after the final direction fix.
- Compile/config loading passed.
- Critical Ruff rules `E9,F63,F7,F82` passed.
- Causality test proves that mutating candles after a decision boundary does
  not alter the already calculated expert verdict.
- A dedicated regression proves an eligible expert LONG score cannot promote
  an existing BEARISH setup: it is capped below the risk threshold.

Several pre-existing legacy `trade-5m-v1` tests remain stale because that
runtime identity was previously removed. They are unrelated to this change and
were not represented as new regressions.

## Deployment and natural-boundary evidence

Final production images:

- orchestrator: `sha256:4e64ec625aaa81eb3ff68b133c97d15747bed993e2d336e3cfecaecd9c6173a3`;
- operator: `sha256:f92a660adde78e9668c017b0c74a3e236de2b34613fc0412dec0562ec856505b`.

Both report source identity
`9e862a3deaac7191eb26032e2dd2b75e7c025301`; restart count is zero. The
operator probe reports `healthy=true`, `foundation_mode=PRODUCTION_PAPER`,
`control_state=CONTINUOUS_ARMED`, generation `20`. Runtime health reports
`mode=PAPER`, `live_allowed=false`, selector/execution workers active, and the
database durability gate ready.

At the closed `2026-11-02 18:00 UTC` boundary, production persisted the new
expert verdict. The observed cohort contained 17 available symbols at the
measurement instant; all 17 had `future_bars_used_count=0` and
`orders_created=0`. Examples:

| Symbol | Expert entry score | Setup direction | Applied strategy score | Result |
|---|---:|---|---:|---|
| ETHUSDT | 69.8097 | BULLISH | 69.8097 | proceeded to normal risk gates, then rejected |
| LINKUSDT | 69.8814 | BULLISH | 69.8814 | proceeded to normal risk gates, then rejected |
| SOLUSDT | 57.7078 | BEARISH | 49.999 | rejected; LONG score not applied |
| XRPUSDT | 58.5121 | BEARISH | 49.999 | rejected; LONG score not applied |
| DOGEUSDT | 71.2582 | BEARISH | 49.999 | rejected; LONG score not applied |

SQL verification found zero BEARISH decisions at or above the entry threshold.
Risk/geometry/economics rejections are expected and demonstrate that weights
do not bypass downstream protections.

## Canary correction

The first post-deploy boundary exposed that an expert score could be attached
to a pre-existing bearish candidate. Safety counters showed zero created
orders and zero opened positions. The strategy layer was immediately corrected
to require `direction_hint=BULLISH`, rebuilt and redeployed. The final natural
boundary above verifies the correction. The superseded intermediate image is
not the deployed image.

## Rollback

Rollback images:

- `traders-ml-online-orchestrator-5m:rollback-pre-bull-run-20261102_204834`;
- `traders-operator-control-api:rollback-pre-bull-run-20261102_204834`.

The pre-deploy YAML is stored at
`reports/deployment/bull_run_calibration_20261102_204834/trade_parameters.predeploy.yaml`.
Rollback must restore that exact YAML and recreate only the orchestrator and
operator from the two rollback tags. PostgreSQL, market-data services and LIVE
state must not be changed.

## Remaining acceptance work

This is an accepted production PAPER deployment, not a profitability guarantee.
Required next evidence is uninterrupted PAPER observation including negative
windows and false entries, followed by the immutable full-November verifier
after `2026-12-01`. LIVE activation remains a separate task requiring explicit
authorization, canary/shadow controls and rollback evidence.
