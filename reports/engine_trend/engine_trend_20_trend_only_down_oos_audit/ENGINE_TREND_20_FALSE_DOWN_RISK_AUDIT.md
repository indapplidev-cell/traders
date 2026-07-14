# ENGINE-TREND-20 — false DOWN risk audit

Potential false DOWN is a provisional control-bucket collision, not a ground-truth error.

Count/rate: **3 / 10.34%**.

| case | bucket | baseline | risk flags |
|---|---|---|---|
| SOLUSDT_15m_2026_07_08_11_30 | POST_DROP_REBOUND_CONTROL | UNKNOWN | none |
| BTCUSDT_15m_2025_08_28_21_45 | RANGE_BEARISH_PRESSURE_CONTROL | UNKNOWN | RANGE_DETECTED |
| ETHUSDT_15m_2025_03_12_03_45 | TRAP_OR_RANGE_CONFLICT_CONTROL | DOWN | RANGE_DETECTED |

Common unsafe conditions are range/flat structure, weak negative progress relative to ATR, post-drop exhaustion, confirmed bullish reversal, and trap/range conflict.
