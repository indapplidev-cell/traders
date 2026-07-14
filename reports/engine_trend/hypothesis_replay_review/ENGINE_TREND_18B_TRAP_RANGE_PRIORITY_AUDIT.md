# ENGINE-TREND-18B — Trap vs Range Priority Audit

## Cases

| Window | Reference → regime | Cause / hypotheses | Verdict |
|---|---|---|---|
| `btcusdt_15m_down_002` | EXPECTED_DOWN → FLAT | CONFIRMED_RANGE:CONFIRMED:0.711;BULL_TRAP:CONFIRMED:0.700 | PRIORITY_ISSUE |
| `ethusdt_15m_up_002` | EXPECTED_UP → FLAT | CONFIRMED_RANGE:CONFIRMED:0.715;BEAR_TRAP:CONFIRMED:0.700 | PRIORITY_ISSUE |

Both cases have `TIME_CONFIRMATION` and a return inside the detected range. Range scores include a +0.15 returned-to-range bonus, producing scores slightly above the fixed 0.70 trap score. Because opposing confirmed hypotheses differ by less than 0.10, `dominant_hypothesis` is correctly unset, although the composer still selects the slightly higher FLAT score.

## Decision

Do not give every confirmed trap unconditional priority over a confirmed range. Add a post-return directional continuation feature first. A trap may outrank range only after evidence beyond the return itself, such as displacement away from the boundary, failure to retest the extreme, or a confirmed directional contextual event. Until then FLAT is the safe result.
