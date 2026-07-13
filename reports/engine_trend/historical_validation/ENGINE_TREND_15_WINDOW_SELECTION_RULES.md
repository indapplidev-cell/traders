# ENGINE-TREND-15 — Window Selection Rules

Candidate selection is performed before engine execution from chronological PostgreSQL OHLC rows only. The selector examines non-overlapping 96-candle blocks, which bounds memory/work and avoids near-duplicate candidates. One strongest deterministic candidate per available type and symbol is frozen; ties prefer the earlier block.

- EXPECTED_UP: return >= 1.5%, efficiency >= 0.45, close in upper half; rank by return, efficiency, close position.
- EXPECTED_DOWN: return <= -1.5%, efficiency >= 0.45, close in lower half; rank by negative return, efficiency, inverse close position.
- EXPECTED_FLAT: absolute return <= 0.5%, range <= 3.0%, efficiency <= 0.25; rank by smallest return, efficiency, range.
- EXPECTED_UNKNOWN_OR_MIXED: absolute return <= 1.0%, range >= 2.5%, efficiency <= 0.35; rank by range, then smallest return and efficiency.
- RECENT_BASELINE: latest 96 candles. Its allowed reference label is provisionally EXPECTED_UNKNOWN_OR_MIXED, while `window_type` preserves RECENT_BASELINE.

No thresholds were relaxed. Breakout/fakeout is deferred because a sufficiently unambiguous first-pack rule was not adopted. Descriptive metrics never enter engine core or comparison logic.
