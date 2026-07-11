# BOOK-L2-02 - Context Quality Score / Symbol Ranking

## Status

PASS

## Implemented

- Added context quality scoring for BOOK-L2 symbols.
- Added quality grades: HIGH, MEDIUM, LOW, SKIP, ERROR.
- Added deterministic symbol ranking.
- Added quality reason codes.
- Added quality summary.
- Added top ranked symbols for observation.
- Updated terminal output with Quality, Score and Rank.
- Updated stable L2 JSON export.
- Preserved observe-only / fail-closed safety.

## Safety

BOOK-L2 remains observe-only.
No LONG / SHORT / BUY / SELL.
No live trading.
No CandleRepository.
No MarketReaderOrchestrator.
No Binance download.

## Checks

- py_compile passed.
- Targeted tests passed.
- Full BOOK-L1 + BOOK-L2 pack passed.
- Fresh L1 export passed.
- L1 JSON consumer strict passed.
- L2 default / strict / details / export smoke passed.
- Forbidden import check passed.

## Conclusion

BOOK-L2 can now rank symbols by context quality for observation while remaining fail-closed and without producing trading signals.
