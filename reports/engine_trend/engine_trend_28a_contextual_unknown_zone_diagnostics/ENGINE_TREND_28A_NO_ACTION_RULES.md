# ENGINE-TREND-28A NO_ACTION rules

`NO_ACTION` is an output of the diagnostic layer, not a trading action.

For every source `UNKNOWN`, diagnostics must return `action=NO_ACTION`, `contextual_state=WAIT_FOR_CONFIRMATION`, `setup_created=false`, and `trade_signal_created=false`. The source regime and confidence are copied unchanged.

The following implications are forbidden:

- `LOCAL_RANGE_UNCONFIRMED` → `FLAT`;
- `NEAR_RESISTANCE` or `NEAR_UPPER_RANGE_BOUNDARY` → short;
- `NEAR_SUPPORT` or `NEAR_LOWER_RANGE_BOUNDARY` → long;
- `BREAKOUT_NOT_CONFIRMED` → short;
- `BREAKDOWN_NOT_CONFIRMED` → long;
- `HIGHER_TF_BEARISH_RISK` → short;
- `HIGHER_TF_BULLISH_RISK` → long;
- indicator vote pressure → setup without a causal hypothesis and confirmed trigger.

`CONFIRMED_RANGE_CONTEXT` may describe `FLAT` or a range/trend conflict, but never changes the source regime. A diagnostic call for a non-`UNKNOWN` source remains context-only and still cannot create a setup.

Confirmation text is descriptive. Bullish confirmation may mention a closed breakout, volume expansion, retest/hold, reversal or continuation follow-through. Bearish confirmation may mention rejection, a closed breakdown, retest/hold and follow-through. These strings do not execute or authorize a trade.
