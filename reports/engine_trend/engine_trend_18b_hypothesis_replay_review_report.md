# ENGINE-TREND-18B — Hypothesis Replay Review and Edge Case Audit

## Decision

**PASS as an audit; HOLD for blind tuning.** The hypothesis architecture remains safety-correct, but DOWN recall and trap/range arbitration require controlled follow-up work.

## Scope

- input rows: 60
- unique market periods: 45
- duplicated rows: 15
- duplicate periods with inconsistent reference labels: 3
- raw target rows: 29
- unique target periods reviewed: 22
- safety or runtime-trading changes: none

The raw pack contains repeated ENGINE-TREND-15 periods under ENGINE-TREND-15B identifiers. Raw counts are retained for compatibility; conclusions use unique `(symbol, interval, period_start, period_end)` fingerprints.

Three duplicated recent-baseline periods are labelled `EXPECTED_UNKNOWN_OR_MIXED` in the older pack and `RECENT_BASELINE` in the expanded pack. This is additional evidence that reference labels are review metadata rather than ground truth.

## Review outcome

| Window | Reference → regime | Cause / hypotheses | Verdict |
|---|---|---|---|
| `btcusdt_15m_down_001` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `btcusdt_15m_down_002` | EXPECTED_DOWN → FLAT | CONFIRMED_RANGE:CONFIRMED:0.711;BULL_TRAP:CONFIRMED:0.700 | PRIORITY_ISSUE |
| `btcusdt_15m_down_003` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `btcusdt_15m_flat_001` | EXPECTED_FLAT → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `btcusdt_15m_flat_002` | EXPECTED_FLAT → UNKNOWN | ONLY_PENDING_NO_CONFIRMED | EXPECTED_CAUTION |
| `btcusdt_15m_mixed_003` | EXPECTED_UNKNOWN_OR_MIXED → UP | BULLISH_REVERSAL:CONFIRMED:0.600 | LABEL_ISSUE |
| `btcusdt_15m_up_001` | EXPECTED_UP → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `btcusdt_15m_up_002` | EXPECTED_UP → FLAT | CONFIRMED_RANGE:CONFIRMED:0.641 | LABEL_ISSUE |
| `btcusdt_15m_up_003` | EXPECTED_UP → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `btcusdt_15m_up_004` | EXPECTED_UP → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `ethusdt_15m_down_001` | EXPECTED_DOWN → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `ethusdt_15m_down_002` | EXPECTED_DOWN → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `ethusdt_15m_down_003` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `ethusdt_15m_up_001` | EXPECTED_UP → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `ethusdt_15m_up_002` | EXPECTED_UP → FLAT | CONFIRMED_RANGE:CONFIRMED:0.715;BEAR_TRAP:CONFIRMED:0.700 | PRIORITY_ISSUE |
| `ethusdt_15m_up_003` | EXPECTED_UP → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `ethusdt_15m_up_004` | EXPECTED_UP → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `solusdt_15m_down_001` | EXPECTED_DOWN → UNKNOWN | ONLY_PENDING_NO_CONFIRMED | EXPECTED_CAUTION |
| `solusdt_15m_down_002` | EXPECTED_DOWN → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `solusdt_15m_down_003` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `solusdt_15m_up_001` | EXPECTED_UP → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `solusdt_15m_up_004` | EXPECTED_UP → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |

Verdicts on unique periods: {"EXPECTED_CAUTION": 11, "PRIORITY_ISSUE": 2, "INSUFFICIENT_CONTEXT": 7, "LABEL_ISSUE": 2}. `RULE_TOO_STRICT` is intentionally not assigned from deterministic labels alone.

## Answers to the audit questions

1. **Why no DOWN?** No bearish reversal reached `AWAITING_CONFIRMATION` or `CONFIRMED`. Confirmed downward breakouts created pending continuations, but whole-window structure was `SIDEWAYS_STRUCTURE` and no confirmed bearish continuation candle supplied the second method.
2. **Why no hypotheses in some windows?** There are 17 raw / 12 unique `NO_HYPOTHESES` periods. They form neither an aligned structure/breakout/event continuation, contextual reversal, detected range, nor returned-to-range trap.
3. **Why PENDING + CONFLICTED?** There are 21 raw / 15 unique cases. A confirmed breakout conflicts the old range while the matching continuation has only one confirming method.
4. **Should trap beat range?** Not unconditionally. Both trap cases have time confirmation, but the current payload has no post-return directional continuation measure. The score gaps (0.011, 0.015) are below the 0.10 dominance margin.
5. **Are 96 candles enough?** Not proven. All audited windows have 96 candles, yet event-local structure can be detected. The audit cannot separate insufficient lookback from unsuitable deterministic labels without a longer-lookback counterfactual replay.

## Gate for ENGINE-TREND-19

Run controlled counterfactuals only: longer prehistory, bearish level availability, continuation cross-method confirmation, and post-trap continuation. Do not lower global thresholds from this pack.
