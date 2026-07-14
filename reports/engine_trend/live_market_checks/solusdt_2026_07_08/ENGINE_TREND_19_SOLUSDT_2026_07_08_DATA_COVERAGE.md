# ENGINE-TREND-19 SOLUSDT 15m — data coverage

Generated: `2026-07-13T17:30:04.359085Z`. Database was queried before Binance.

| scope | expected | DB before | first after | last after | missing after | duplicates after | source | status |
|---|---:|---:|---|---|---:|---:|---|---|
| SOLUSDT_15m_2026_07_08 | 96 | 0 | 2026-07-08T00:00:00Z | 2026-07-08T23:45:00Z | 0 | 0 | BINANCE_ONLY | PASS |
| SOLUSDT_2026_07_08_06_00 | 96 | 0 | 2026-07-07T06:15:00Z | 2026-07-08T06:00:00Z | 0 | 0 | BINANCE_ONLY | PASS |
| SOLUSDT_2026_07_08_11_30 | 96 | 0 | 2026-07-07T11:45:00Z | 2026-07-08T11:30:00Z | 0 | 0 | BINANCE_ONLY | PASS |
| SOLUSDT_2026_07_08_18_30 | 96 | 0 | 2026-07-07T18:45:00Z | 2026-07-08T18:30:00Z | 0 | 0 | BINANCE_ONLY | PASS |
| SOLUSDT_2026_07_08_23_45 | 96 | 0 | 2026-07-08T00:00:00Z | 2026-07-08T23:45:00Z | 0 | 0 | BINANCE_ONLY | PASS |

## Backfill operations

```json
[
  {
    "start": "2026-07-07T06:15:00Z",
    "end_exclusive": "2026-07-09T00:00:00Z",
    "requested_missing_intervals": 167,
    "downloaded_closed_candles": 167,
    "inserted_missing_candles": 167
  }
]
```

## Data-quality checks

```json
{
  "main": {
    "status": "PASS",
    "checks": {
      "expected_count": true,
      "no_missing_intervals": true,
      "no_duplicates": true,
      "regular_15m": true,
      "timezone_utc": true,
      "ohlc_consistency": true,
      "no_nan_or_inf": true,
      "positive_ohlc": true,
      "non_negative_volume": true,
      "closed_candles_only": true
    },
    "failed_checks": []
  },
  "windows": {
    "SOLUSDT_2026_07_08_06_00": {
      "status": "PASS",
      "checks": {
        "expected_count": true,
        "no_missing_intervals": true,
        "no_duplicates": true,
        "regular_15m": true,
        "timezone_utc": true,
        "ohlc_consistency": true,
        "no_nan_or_inf": true,
        "positive_ohlc": true,
        "non_negative_volume": true,
        "closed_candles_only": true
      },
      "failed_checks": []
    },
    "SOLUSDT_2026_07_08_11_30": {
      "status": "PASS",
      "checks": {
        "expected_count": true,
        "no_missing_intervals": true,
        "no_duplicates": true,
        "regular_15m": true,
        "timezone_utc": true,
        "ohlc_consistency": true,
        "no_nan_or_inf": true,
        "positive_ohlc": true,
        "non_negative_volume": true,
        "closed_candles_only": true
      },
      "failed_checks": []
    },
    "SOLUSDT_2026_07_08_18_30": {
      "status": "PASS",
      "checks": {
        "expected_count": true,
        "no_missing_intervals": true,
        "no_duplicates": true,
        "regular_15m": true,
        "timezone_utc": true,
        "ohlc_consistency": true,
        "no_nan_or_inf": true,
        "positive_ohlc": true,
        "non_negative_volume": true,
        "closed_candles_only": true
      },
      "failed_checks": []
    },
    "SOLUSDT_2026_07_08_23_45": {
      "status": "PASS",
      "checks": {
        "expected_count": true,
        "no_missing_intervals": true,
        "no_duplicates": true,
        "regular_15m": true,
        "timezone_utc": true,
        "ohlc_consistency": true,
        "no_nan_or_inf": true,
        "positive_ohlc": true,
        "non_negative_volume": true,
        "closed_candles_only": true
      },
      "failed_checks": []
    }
  }
}
```
