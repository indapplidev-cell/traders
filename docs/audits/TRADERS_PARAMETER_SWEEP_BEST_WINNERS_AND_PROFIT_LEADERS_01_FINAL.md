# Parameter Sweep profit and win leaders — final decision

```text
TASK = TRADERS_PARAMETER_SWEEP_BEST_WINNERS_AND_PROFIT_LEADERS_01
FINAL_STATUS = PASS
FINAL_VERDICT = PASS_BEST_PROFIT_AND_WIN_COUNT_RESULTS
PROFILE = trade-5m-v2
SELECTED_SYMBOL = SOLUSDT
RUN_ID = 20260915_074652_882
TOTAL_EVALUATED_CONFIGS = 525
WINNER_POPULATION = ALL_EVALUATED_RESEARCH_CONFIGS
VALIDATION_FILTER_APPLIED_TO_ANALYTICAL_WINNERS = false
LIVE = DISABLED
BINANCE_ORDER_API_CALLS = 0
PRODUCTION_MUTATIONS = 0
FIFTEEN_MINUTE_PROFILE_CHANGED = false
```

## Proven result

The bounded streaming tracker persists and resumes three analytical incumbents:
best strictly positive Net PnL, best Net PnL fallback, and greatest win count.
Ranking is deterministic, validation eligibility does not hide a winner, and
behavioral aliases are deduplicated while numeric alias counts remain visible.
The incumbent projections retain dynamic parameter maps and the complete
economic/validation metric contract.  Adaptive refinement receives the distinct
profit, win-count, and balanced incumbents as candidate parents without treating
win count as an economic objective.

The real Tk run found positive Net PnL.  Its positive leader is config
`e871690f32e76cb937d2ea92812a0237eb9b18eea394fed5b24e05d5f683cfa2`:
3 trades, 2 wins, 1 loss, gross PnL 2.8638032721, costs 2.0369317200,
modeled slippage 0.3545176038, Net PnL 0.8268715521, expectancy 0.2756238507,
profit factor 2.9882008316, max drawdown 0.4158893503.  Validation is
`INSUFFICIENT_SAMPLE`; promotion eligibility is false, but the analytical result
remains visible as required.

The win-count leader is config
`f2b7e1e014b9883fa326786cccd2f3d76967230ff02da760e03b3dd97b183401`:
79 trades, 24 wins, 55 losses, gross PnL 10.4424170815, costs 41.6494020513,
modeled slippage 7.2471725732, Net PnL -31.2069849698, expectancy
-0.3950251262, profit factor 0.1441829260, max drawdown 32.1263259514.
The Tk card explicitly labels its economic result as negative.

## Acceptance evidence

- Canonical artifact: `artifacts/scalping_v2_parameter_sweep/20260915_074652_882/BEST_CONFIGS.json`.
- Machine-readable evidence: `docs/audits/TRADERS_PARAMETER_SWEEP_BEST_WINNERS_AND_PROFIT_LEADERS_01_ACCEPTANCE.json`.
- Final desktop preflight: PID 24044, HWND 3081200, PASS for session,
  WinSta0/Default desktop, integrity, visibility, responsiveness and foreground.
- Capture mode: `FULL_DESKTOP_CROPPED_BY_HWND`; crop SHA-256
  `6D8EEB9DBA76431DCFA00C96E362C1970CE911DDE0A718780949E4A8912326C7`.
- Visual verdict: both cards show all dynamic parameters and metrics; the
  win-count card shows the explicit negative-economics warning.
- Active config SHA-256 before/after:
  `ae838771a9c8a44dd8ed2fe4b00c4654428eeb44fc7fc4be98d8ec2290baa4f4`.

## Verification

```text
CHANGED_SCOPE = 106 passed, 1 deselected
HISTORICAL_REPLAY_POST_SLIPPAGE = 8 passed
COMPILEALL = PASS
SERVER_BROAD = 438 passed, 11 failed, 1 deselected
CLIENT_FOCUSED = 6 passed
CLIENT_BROAD = 1517 passed, 2 skipped, 3029 subtests passed, 1 failed
```

The server broad failures are pre-existing contract/test drift outside this
change: eight legacy finding-verifier fixtures omit the now-required `reload`
section, one stale score-band assertion expects 55 instead of the current
production baseline, and two old Tk assertions expect mojibake text.  The one
client broad failure is likewise a pre-existing mojibake expectation.  No
changed winner, replay, checkpoint, adaptive, GUI projection, or i18n-sync test
failed.
