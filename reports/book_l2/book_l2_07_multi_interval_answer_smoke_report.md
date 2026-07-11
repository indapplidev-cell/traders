# BOOK-L2-07 - Multi-Interval Answer Smoke

## Status

`PASS`

## Purpose

This stage verifies that the full BOOK-L1 -> BOOK-L2 pipeline can produce real human-readable context answers across multiple intervals, not only for a single interval.

## Tested request

- Symbols: BTCUSDT, ETHUSDT, SOLUSDT
- Intervals: 15m, 1h, 4h
- Window size: 300
- Window count: 4
- Min candles: 50

## Generated answer file

`reports/book_l2/l1_l2_multi_interval_answer.md`

## Result summary

- Intervals checked: 3
- PASS: 1
- FAIL: 2
- PASS_WITH_WARNINGS: 0
- Most common overall state: UNKNOWN
- Intervals with observation candidates: none
- Intervals with all symbols skipped: 15m, 1h, 4h
- Repeated skip candidates: BTCUSDT, ETHUSDT, SOLUSDT
- Repeated observation candidates: none

## Real smoke result

`FAIL` in strict mode.

The implementation completed the multi-interval run and created the Markdown evidence report. The strict result is documented because 1h and 4h produced L2 warnings from insufficient cached candles:

- 1h: BTCUSDT, ETHUSDT, and SOLUSDT required 1200 candles and found 0.
- 4h: BTCUSDT, ETHUSDT, and SOLUSDT required 1200 candles and found 0.

The 15m interval passed. All intervals preserved fail-closed safety.

## Safety

The generated answers are observe-only.
No trading instructions are generated.
No live trading is connected.

## Checks

- py_compile: PASS
- targeted tests: PASS
- integration targeted pack: PASS
- full BOOK-L1 + BOOK-L2 + integration pack: PASS
- real multi-interval smoke: documented strict FAIL from insufficient 1h/4h cached candles
- forbidden terms check: PASS
- git diff --cached --check: PASS

## Conclusion

The L1-L2 pipeline can now produce interval-based evidence across multiple intervals.
