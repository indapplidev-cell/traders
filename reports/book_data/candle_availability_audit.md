# BOOK-DATA-01 - Candle Data Availability Audit

## Status

`PASS`

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT |
| Intervals | 15m |
| Window size | 300 |
| Window count | 4 |
| Required candles | 1200 |

## Availability

| Symbol | Interval | Available | Required | Status | First open time | Last open time | Message |
|---|---|---:|---:|---|---|---|---|
| BTCUSDT | 15m | 1200 | 1200 | READY | 2026-01-01T00:00:00+00:00 | 2026-01-02T00:00:00+00:00 | ready for L1-L2 report |

## Summary

| Status | Count |
|---|---:|
| READY | 1 |
| INSUFFICIENT_DATA | 0 |
| MISSING | 0 |
| ERROR | 0 |

## Conclusion

- Ready intervals: 15m
- Missing intervals: none
- Insufficient intervals: none
- Intervals that currently block L1-L2 multi-interval smoke: none

## Safety

- read_only: `true`
- download_executed: `false`
- db_write_executed: `false`
- safe_for_runtime_trading: `false`
