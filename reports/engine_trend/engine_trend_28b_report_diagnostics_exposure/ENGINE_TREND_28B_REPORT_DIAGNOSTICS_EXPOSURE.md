# ENGINE-TREND-28B — Offline report diagnostics exposure

## Decision

ENGINE-TREND-28A contextual diagnostics are now attached to ENGINE-TREND replay JSON under the optional top-level field `contextual_diagnostics`. The same section is rendered in per-window Markdown as explicitly offline, diagnostic, and non-signal output.

The attachment point is `scripts/engine_trend_18_hypothesis_replay.build_diagnostic`, after the engine and composer have finalized the result. The adapter receives the completed artifact and returns a copy with one new field. It does not feed any value back into engine, composer, setup selection, profitability labels, or trading runtime.

## Artifact contract

The new section exposes:

- `diagnostic_tags` and `no_trade_reasons` from the 28A vocabulary;
- `action: NO_ACTION` and `contextual_state`;
- price, nearest-zone, range, breakout, indicator, hypothesis, and MTF explanation data when observable;
- `observability`, with each input group marked `observable` or `not_observable`;
- safety assertions that source regime is preserved and no setup or trade signal is created;
- `artifact_contract`, identifying the post-decision offline attachment point.

Historical artifacts do not always contain candles, indicator context, zone distance inputs, or MTF snapshots. Missing groups are marked `not_observable`. Missing input never means that risk is absent and is never converted into a negative observation. In particular, old artifacts without candle values do not receive inferred `NEAR_SUPPORT` or `NEAR_RESISTANCE` results.

## Decision invariants

- `UNKNOWN` plus `NO_ACTION` remains `UNKNOWN`.
- `FLAT` plus `CONFIRMED_RANGE_CONTEXT` remains `FLAT`.
- Composer regime, confidence, decision reason, comparison fields, safety, and setup eligibility are copied without mutation.
- Diagnostics cannot create a setup or a trade signal.
- Runtime, trading runtime, thresholds, composer, and setup contracts are unchanged.

The stage formula remains: 28A explains UNKNOWN; 28B makes the explanation visible in reports; 28B does not solve UNKNOWN.

## Verification scope

`tests/test_engine_trend_28b_report_diagnostics_exposure.py` covers attachment to saved and newly generated replay artifacts, value-equivalent preservation of existing artifact fields, UNKNOWN and FLAT invariants, setup and signal non-interference, and explicit historical observability. The required 28A test and complete `tests/test_engine_trend_*.py` suite are the regression gates.
