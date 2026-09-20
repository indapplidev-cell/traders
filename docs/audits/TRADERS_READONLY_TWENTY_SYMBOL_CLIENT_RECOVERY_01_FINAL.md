# Traders read-only twenty-symbol client recovery — final evidence

RECONCILED_AT_UTC = 2026-09-20T19:22:00Z
PROJECT_STATE_COMMIT = ddb76c8c265f8dfcd5743329e727ff30fdaeb188
FINAL_VERDICT = PASS

## Reported failure

The production Tk client connected to `Production Readonly HTTP`, but Market,
Trading pairs, Analysis, Scenarios, and Funnel displayed a server error after
activation of `trading-universe-v3`.

## Root causes and remediation

1. Read-only response models and the aggregate analysis repository retained
   the historical exact-10 bound. They now consume the shared maximum of 20.
2. Trading-universe readiness coupled its six collected timeframes to the
   active Scalping strategy's four-timeframe window map, producing `KeyError:
   '4h'`. The readiness projection now preserves the original independent
   six-timeframe preparation thresholds.
3. The funnel row-cache timestamp was recorded before a slow materialization.
   A 20-symbol query could exceed the 30-second TTL and therefore be expired as
   soon as it completed, forcing concurrent desktop pages to repeat the SQL.
   TTL now begins after successful materialization.

No strategy, risk, selector, PAPER authority, runtime settings, or YAML file
was changed.

## Verification

- Focused regression suite: `70 passed in 18.40s`.
- Read-only container: `healthy`.
- Image revision label: `ddb76c8c265f8dfcd5743329e727ff30fdaeb188`.
- `/api/v1/trading-universe`: HTTP 200, active version
  `trading-universe-v3`, active symbols 20, preflight PASS 20, ready streams
  120.
- `/api/v1/analysis`: HTTP 200, active scope 20, returned items 20.
- `/api/v1/trading/funnel?trade_profile=trade-5m-v2`: HTTP 200,
  `universe_symbols=20`, current cycle expected/seen/processed `20/20/20`,
  freshness `CURRENT`.
- Warm materialization: HTTP 200 in 29.121 seconds.
- Four concurrent cached funnel reads: all HTTP 200 in
  10.942–12.230 seconds.
- PAPER readiness remains `READY`, schema
  `0034_scalping_universe_v3`, control `CONTINUOUS_ARMED`, generation 15,
  `live_allowed=false`.

The wider `tests/server_api tests/trading_universe` run remained at the known
unrelated baseline of 9 failures (stale route-count/i18n/service-memory
expectations) with 206 passed and 7 skipped. None of those failures exercises
the corrected twenty-symbol projection paths.

## Desktop acceptance

- PID 16348, HWND 67222.
- Session 1, `WinSta0`, input/target desktop `Default`, integrity `MEDIUM`.
- Preflight, foreground activation, responsiveness, and full-desktop cropped
  capture: PASS.
- UIA absence: non-blocking per project policy.
- Final crop SHA-256:
  `2A33803D56EA80DCA0AD3E19D9DDB81E4D48DA3C04D88B0FF304BB811BB1C165`.
- Visible Tk Funnel evidence: connection healthy; Scalping selected; current
  cycle `Обработано: 20 / 20`; last completed cycle `Обработано: 20 / 20`;
  production symbols including newly activated ZEC/ENA/FET/FIL visible.
- Safety: read-only navigation only; mutation controls 0; LIVE enablement 0;
  real Binance order calls 0; secret output 0.
