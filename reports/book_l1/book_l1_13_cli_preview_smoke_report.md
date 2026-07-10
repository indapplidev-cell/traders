# BOOK-L1-13 - CLI Preview Manual Smoke / Real DB Preview Report

## Status

`PASS`

## Run context

- Generated at UTC: `2026-07-10T20:35:02.941789+00:00`
- Command: `python -m app.cli.commands book-l1-preview --symbol BTCUSDT --interval 15m --limit 300 --min-candles 50`
- Source: local PostgreSQL candle cache through `CandleRepository.get_last_n()`
- Trading execution: disabled
- Model training: not executed
- Binance download: not executed
- Runtime trading integration: not connected

## Input

- Symbol: `BTCUSDT`
- Interval: `15m`
- Requested limit: `300`
- Candle count used: `300`
- First open time: `2026-06-12T17:15:00+00:00`
- Last open time: `2026-06-15T20:00:00+00:00`

## BOOK-L1 output

- Market regime: `FLAT`
- Directional bias: `NEUTRAL`
- Confidence: `0.9406046268096556`
- Trend strength: `NONE`
- Trade signal: `NOT_EVALUATED`
- Safe for runtime trading: `false`

## Reason codes

- `MARKET_READER_ORCHESTRATED`
- `MARKET_REGIME_COMPOSED`
- `COMPOSER_FLAT_RANGE_DOMINANT`
- `UP_TREND_STRUCTURE`
- `HIGHER_HIGHS`
- `HIGHER_LOWS`
- `RANGE_STRUCTURE_DETECTED`
- `RANGE_WIDTH_ACCEPTABLE`
- `LOW_CLOSE_DRIFT_INSIDE_RANGE`
- `SUPPORT_TOUCHES_DETECTED`
- `RESISTANCE_TOUCHES_DETECTED`
- `NO_CLOSE_BREAKOUT`
- `PRICE_INSIDE_RANGE`
- `EMA_TREND_MIXED`
- `FAST_EMA_BELOW_SLOW_EMA`
- `PRICE_BELOW_EMAS`
- `ATR_NORMAL_VOLATILITY`

## Safety notes

- Safety invariants are satisfied.

## Expected safety contract

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
```

## Conclusion

BOOK-L1 CLI preview successfully reads real stored candles from DB and returns a market-reading result only. It does not produce a trading signal and does not approve runtime trading.
