# ENGINE-TREND-15 — Historical Market Reading Validation Summary

## Purpose
Validate how the unchanged engine reads transparently selected historical OHLC windows. Reference labels are validation references, not trading signals.

## Data source
Read-only `public.market_candles` in PostgreSQL 16.10; no report JSON was used as a candle source.

## Validation scope
15 windows; BTCUSDT, ETHUSDT, SOLUSDT; 15m; 96 candles per window.

## Window selection rules
Selection used raw OHLC descriptive metrics before any engine invocation. Full frozen rules are in `ENGINE_TREND_15_WINDOW_SELECTION_RULES.md`.

## Selected windows
- `btc_15m_expected_up_001`: EXPECTED_UP, 2026-02-06T00:00:00+00:00 — 2026-02-06T23:45:00+00:00
- `btc_15m_expected_down_001`: EXPECTED_DOWN, 2026-02-05T00:00:00+00:00 — 2026-02-05T23:45:00+00:00
- `btc_15m_expected_flat_001`: EXPECTED_FLAT, 2025-09-27T00:00:00+00:00 — 2025-09-27T23:45:00+00:00
- `btc_15m_expected_unknown_or_mixed_001`: EXPECTED_UNKNOWN_OR_MIXED, 2025-01-20T00:00:00+00:00 — 2025-01-20T23:45:00+00:00
- `btc_15m_recent_baseline_001`: EXPECTED_UNKNOWN_OR_MIXED, 2026-06-14T20:15:00+00:00 — 2026-06-15T20:00:00+00:00
- `eth_15m_expected_up_001`: EXPECTED_UP, 2025-05-08T00:00:00+00:00 — 2025-05-08T23:45:00+00:00
- `eth_15m_expected_down_001`: EXPECTED_DOWN, 2026-02-05T00:00:00+00:00 — 2026-02-05T23:45:00+00:00
- `eth_15m_expected_flat_001`: EXPECTED_FLAT, 2025-09-08T00:00:00+00:00 — 2025-09-08T23:45:00+00:00
- `eth_15m_expected_unknown_or_mixed_001`: EXPECTED_UNKNOWN_OR_MIXED, 2025-02-03T00:00:00+00:00 — 2025-02-03T23:45:00+00:00
- `eth_15m_recent_baseline_001`: EXPECTED_UNKNOWN_OR_MIXED, 2026-06-14T20:30:00+00:00 — 2026-06-15T20:15:00+00:00
- `sol_15m_expected_up_001`: EXPECTED_UP, 2025-03-02T00:00:00+00:00 — 2025-03-02T23:45:00+00:00
- `sol_15m_expected_down_001`: EXPECTED_DOWN, 2025-03-03T00:00:00+00:00 — 2025-03-03T23:45:00+00:00
- `sol_15m_expected_flat_001`: EXPECTED_FLAT, 2026-04-25T00:00:00+00:00 — 2026-04-25T23:45:00+00:00
- `sol_15m_expected_unknown_or_mixed_001`: EXPECTED_UNKNOWN_OR_MIXED, 2025-01-24T00:00:00+00:00 — 2025-01-24T23:45:00+00:00
- `sol_15m_recent_baseline_001`: EXPECTED_UNKNOWN_OR_MIXED, 2026-06-14T20:30:00+00:00 — 2026-06-15T20:15:00+00:00

## Result matrix summary
Match statuses: {'ACCEPTABLE_UNKNOWN': 3, 'MATCH': 3, 'QUESTIONABLE_UNKNOWN': 9}. Engine regimes: {'UNKNOWN': 15}.

## Per-label outcome summary
Reference-label counts: {'EXPECTED_DOWN': 3, 'EXPECTED_FLAT': 3, 'EXPECTED_UNKNOWN_OR_MIXED': 6, 'EXPECTED_UP': 3}. Row-level outcomes and notes are preserved in both matrix formats.

## Safety contract verification
All 15 results preserve `NOT_EVALUATED`, `safe_for_runtime_trading=false`, and `live_trading_connected=false`; zero violations.

## Important observations
UNKNOWN outcomes are separated into acceptable and questionable cases. Mismatches and review cases are evidence for ENGINE-TREND-16 review, not automatic evidence that core logic is defective.

## What this validation proves
Real database windows can be selected without engine leakage, replayed through the existing boundary/provider pipeline, and compared reproducibly while preserving safety.

## What this validation does not prove
- no trading edge proven
- no profitability proven
- no runtime trading allowed
- no execution readiness proven
- no threshold tuning performed
- no model training performed

## Recommended next decision
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision. Review UNKNOWN and mismatches; do not connect runtime trading.
