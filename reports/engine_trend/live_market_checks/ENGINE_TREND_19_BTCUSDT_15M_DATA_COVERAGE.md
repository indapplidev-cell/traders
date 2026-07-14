# ENGINE-TREND-19 BTCUSDT 15m Data Coverage

Generated at: `2026-07-13T16:26:57.955337Z`. Database was checked before any Binance request.

| period_id | requested_start | requested_end | actual_start | actual_end | expected | found_before_backfill | missing_before_backfill | duplicates_before_backfill | source | found_after_backfill | missing_after_backfill | duplicates_after_backfill | status |
|---|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| BTCUSDT_15m_2026_07_10 | 2026-07-10T00:00:00Z | 2026-07-10T23:45:00Z | 2026-07-10T00:00:00Z | 2026-07-10T23:45:00Z | 96 | 0 | 96 | 0 | DB_PLUS_BINANCE_BACKFILL | 96 | 0 | 0 | PASS |
| BTCUSDT_15m_2026_07_12 | 2026-07-12T00:00:00Z | 2026-07-12T23:45:00Z | 2026-07-12T00:00:00Z | 2026-07-12T23:45:00Z | 96 | 0 | 96 | 0 | DB_PLUS_BINANCE_BACKFILL | 96 | 0 | 0 | PASS |
| BTCUSDT_15m_2026_07_13 | 2026-07-13T00:00:00Z | 2026-07-13T16:00:00Z | 2026-07-13T00:00:00Z | 2026-07-13T16:00:00Z | 65 | 0 | 65 | 0 | DB_PLUS_BINANCE_BACKFILL | 65 | 0 | 0 | PASS |

## Backfill operations

```json
[
  {
    "start": "2026-07-10T00:00:00Z",
    "end_exclusive": "2026-07-11T00:00:00Z",
    "requested_missing_intervals": 96,
    "downloaded_closed_candles": 96,
    "upserted": 96
  },
  {
    "start": "2026-07-12T00:00:00Z",
    "end_exclusive": "2026-07-13T16:15:00Z",
    "requested_missing_intervals": 161,
    "downloaded_closed_candles": 161,
    "upserted": 161
  }
]
```
