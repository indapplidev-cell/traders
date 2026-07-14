# ENGINE-TREND-18B — DOWN Confirmation Audit

## Finding

The absence of DOWN is a real recall gap, but this replay does not prove that a threshold is too strict.

- expected-DOWN target rows: 12 raw / 9 unique
- expected-DOWN UNKNOWN: 8 unique
- expected-DOWN FLAT: 1 unique
- confirmed `BEARISH_REVERSAL`: 0
- confirmed `DOWN_CONTINUATION`: 0
- confirmed bearish hypothesis: one `BULL_TRAP`, which lost to range by 0.011
- bearish reversal event statuses on unique periods: {"CONTEXT_REJECTED": 1199, "CANDIDATE": 43, "INVALIDATED": 19}
- bearish reversal candidate zones: {"NO_CAUSAL_ZONE": 40, "AT_SUPPORT": 3}

No bearish reversal candidate had the required causal resistance context: candidates were at `NO_CAUSAL_ZONE` or `AT_SUPPORT`. Therefore the main bottleneck is contextual eligibility, not follow-through alone.

Confirmed downward breakouts remain pending because cross-method confirmation requires aligned bearish structure or a confirmed bearish continuation event. The audited final structures are sideways.

## Decision

Classify current UNKNOWN outcomes as `EXPECTED_CAUTION` or `INSUFFICIENT_CONTEXT`, not automatically `RULE_TOO_STRICT`. ENGINE-TREND-19 should test longer prehistory and causal resistance construction before changing confirmation thresholds.

| Window | Reference → regime | Cause / hypotheses | Verdict |
|---|---|---|---|
| `btcusdt_15m_down_001` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `btcusdt_15m_down_002` | EXPECTED_DOWN → FLAT | CONFIRMED_RANGE:CONFIRMED:0.711;BULL_TRAP:CONFIRMED:0.700 | PRIORITY_ISSUE |
| `btcusdt_15m_down_003` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `ethusdt_15m_down_001` | EXPECTED_DOWN → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `ethusdt_15m_down_002` | EXPECTED_DOWN → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `ethusdt_15m_down_003` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
| `solusdt_15m_down_001` | EXPECTED_DOWN → UNKNOWN | ONLY_PENDING_NO_CONFIRMED | EXPECTED_CAUTION |
| `solusdt_15m_down_002` | EXPECTED_DOWN → UNKNOWN | NO_HYPOTHESES | INSUFFICIENT_CONTEXT |
| `solusdt_15m_down_003` | EXPECTED_DOWN → UNKNOWN | PENDING_PLUS_CONFLICTED_NO_CONFIRMED | EXPECTED_CAUTION |
