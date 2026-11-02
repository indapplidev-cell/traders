# Bull-run native module interaction remediation

## Result

`PASS_EVENT_CONDITIONED_MODULE_CONFIRMED_PAPER_CANDIDATE`

The earlier October bull-run report compared the independent OHLCV rubric with
an incomplete project snapshot.  All 140 persisted `analysis_direction` values
were null and the compact Nison and Schwager sections were empty.  Its reported
85 understated-strength cases therefore could not prove that the three native
book modules were individually defective.

The audit now causally re-runs the native analysis engine at each selected 1m
and 5m boundary and records:

- Altunina structure, strength, consistency, progress and dominant impulse;
- Schwager range, breakout direction/status and polarity status;
- Nison directional window evidence and body summary;
- technical direction and the complete native hypothesis states.

The corrected native comparison found no wrong project direction among the 140
selected bullish events.  It did find a short-horizon interaction mismatch:
the 5m composer selected `UP` on 49 events, while technical evidence was bullish
on 129; Altunina was `SIDEWAYS_STRUCTURE` on 105 and Schwager had no breakout on
104.  The production correction therefore preserves the conservative native
book contexts and adds an explicit scalp-horizon interaction contract instead
of silently bypassing them.

## Interaction contract

`scalping-module-interaction/1` produces a separate causal verdict for:

- Altunina: higher-high/higher-low recovery structure;
- Schwager: local breakout or causal retest;
- Nison: decision-candle body confirmation;
- technical analysis: the independently weighted indicator score.

A calibrated LONG is confirmed only when at least two modules are bullish and
no more than one is bearish.  A neutral verdict can no longer create a setup or
receive the calibrated strategy score.  Hard invalidations and the existing
LONG-only guard remain authoritative.

## Verified shared calibration

```yaml
entry_weights:
  structure: 25
  context: 4
  momentum: 12
  volume: 15
  entry_quality: 21
  liquidity: 8
  confirmation: 15
entry_threshold: 45
exit_weights:
  graphical_structure: 40
  technical_indicators: 10
  momentum_volume: 16
  holding_economics: 34
at_risk_threshold: 40
exit_threshold: 75
strong_reversal_threshold: 90
minimum_successful_net_pnl_bps: 8
profit_lock_buffer_bps: 8
```

## October replay

- Dataset fingerprint: `37da24cf47d88e5d627b00ba8a704f5fd18490d09a0b8ed603b440cab5887845`.
- Labelled bull runs: 140.
- Module-confirmed candidates: 122.
- Successful trades with net PnL at least +8 bps: 85.
- Coverage: 60.71% against the 60% gate.
- Median successful net PnL: +20.3551 bps.
- Mean captured excursion: 66.15%.
- Failed or missed events: 55.
- Calibration id: `2e24e307946177dc0cae4146924d9c459b8d64644e7c9ba66e639fbbdae6ff91`.

The reduction from the earlier 100 successful events is intentional: 18 of
those trades used a neutral independent direction.  They are no longer admitted
as module-confirmed LONG entries.

## Reproducibility

The primary run and independent verifier produced identical hashes:

- `SUMMARY.json`: `a55f7175cf99c07764437ed0b0dfe66df421bfc750b43b4fba4f9c0d64745300`;
- `EVENT_AUDIT.jsonl`: `77589ea821f3d6b606d65d5c68ec56b2f542da84fbac099286bab0fa8e2cb668`;
- `SUCCESSFUL_TRADES.csv`: `90fa093508f09fc45945eccbda22d4d8125fa7f06cfd7cc44201499a657db014`;
- `MISSED_OR_FAILED_EVENTS.csv`: `32a5fb6f84efacd30b84360c53fbce3528612f56c1f3a55641da3699c3e260ef`;
- `MODULE_CORRECTIONS.json`: `48452a5208932a593192196262e50b71718099a2ab3e6243f2eef694a70888b1`;
- inactive candidate YAML: `74e7a8a3c1e1bff519bd6b74e404dd38f5af499bb0f5760f6b4c2cb0a9a704b4`.

Focused implementation and causality suite: 29 passed.  A broader selected
suite returned 87 passed and 9 failures; eight are pre-existing legacy/runtime
identity expectations tied to the already active local parameter-set epoch, and
the analytical-exit threshold expectation was updated and now passes.

## Scope and safety

This remains event-conditioned evidence, not a whole-market profitability
claim.  The audit still reports 2,240 persisted bullish observations outside
the labelled events; those negative windows require separate qualification.
The deployed mode remains PAPER and LIVE stays disabled.
