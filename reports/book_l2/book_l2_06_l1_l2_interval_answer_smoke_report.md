# BOOK-L2-06 - L1-L2 Interval Report Answer Smoke

## Status

`PASS`

## Purpose

This stage verifies that the full BOOK-L1 -> BOOK-L2 pipeline produces an actual human-readable market context answer for a requested interval, not only green tests.

## Tested request

- Symbols: BTCUSDT, ETHUSDT, SOLUSDT
- Interval: 15m
- Window size: 300
- Window count: 4
- Min candles: 50

## Generated answer file

`reports/book_l2/l1_l2_interval_answer.md`

## Pipeline checks

- L1 timeline export: PASS
- L1 JSON consumer strict: PASS
- L2 context export: PASS
- L2 JSON consumer strict: PASS
- L2 API readiness strict: PASS
- Symbol propagation: PASS
- Source lineage: PASS
- Fail-closed safety: PASS
- Evidence Markdown written: PASS

## Safety

The generated answer is observe-only.
It contains no trading instructions.
No live trading is connected.

## Conclusion

The L1-L2 pipeline can produce a real interval-based context report for human review.
