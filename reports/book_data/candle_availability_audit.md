# BOOK-DATA-01 - Candle Data Availability Audit

## Status

`PASS_WITH_DATA_GAPS`

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Intervals | 15m, 1h, 4h |
| Window size | 300 |
| Window count | 4 |
| Required candles | 1200 |

## Availability

| Symbol | Interval | Available | Required | Status | First open time | Last open time | Message |
|---|---|---:|---:|---|---|---|---|
| BTCUSDT | 15m | 50961 | 1200 | READY | 2025-01-01T00:00:00+00:00 | 2026-06-15T20:00:00+00:00 | ready for L1-L2 report |
| BTCUSDT | 1h | 0 | 1200 | MISSING | N/A | N/A | no candles found |
| BTCUSDT | 4h | 0 | 1200 | MISSING | N/A | N/A | no candles found |
| ETHUSDT | 15m | 50962 | 1200 | READY | 2025-01-01T00:00:00+00:00 | 2026-06-15T20:15:00+00:00 | ready for L1-L2 report |
| ETHUSDT | 1h | 0 | 1200 | MISSING | N/A | N/A | no candles found |
| ETHUSDT | 4h | 0 | 1200 | MISSING | N/A | N/A | no candles found |
| SOLUSDT | 15m | 50962 | 1200 | READY | 2025-01-01T00:00:00+00:00 | 2026-06-15T20:15:00+00:00 | ready for L1-L2 report |
| SOLUSDT | 1h | 0 | 1200 | MISSING | N/A | N/A | no candles found |
| SOLUSDT | 4h | 0 | 1200 | MISSING | N/A | N/A | no candles found |

## Summary

| Status | Count |
|---|---:|
| READY | 3 |
| INSUFFICIENT_DATA | 0 |
| MISSING | 6 |
| ERROR | 0 |

## Conclusion

- Ready intervals: 15m
- Missing intervals: 1h, 4h
- Insufficient intervals: none
- Intervals that currently block L1-L2 multi-interval smoke: 1h, 4h

## Safety

- read_only: `true`
- download_executed: `false`
- db_write_executed: `false`
- safe_for_runtime_trading: `false`
