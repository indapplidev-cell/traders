# ENGINE-TREND-19 — Technical Analysis Core Hardening

## Result

The Nison/Altunina/Schwager core now accepts a production-grade OHLCV series, separates context from recent decisions and event-local confirmation, uses volatility-aware structure, exposes classical technical confirmation, supports multi-timeframe confluence, and returns exactly one explicit final regime.

`UNKNOWN` remains a valid unambiguous answer: no non-conflicted confirmed hypothesis is currently available.

## Limitation closure

### 1. Minimum candle contract

- full analysis minimum: 64 candles;
- recommended structural context: 96 candles;
- shorter public inputs fail closed to `UNKNOWN` with `COMPOSER_PARTIAL_ANALYSIS_UNKNOWN`;
- low-level book-rule functions retain short synthetic fixtures for isolated testing.

### 2. Timestamp and cadence validation

- ISO-8601, unix seconds, and unix milliseconds are parsed to UTC;
- exchange intervals such as `15m`, `1h`, and `1d` are parsed explicitly;
- reversed timestamps, duplicate timestamps, sub-interval cadence, and missing-candle gaps are reported separately;
- strict production batches with cadence errors have `VALIDATION_FAILED` status.

### 3. Numeric market-data validation

- public row normalization rejects `NaN`, positive/negative infinity, and non-positive prices;
- composer integrity independently rejects non-finite or non-positive OHLC values;
- volume must remain finite and non-negative.

### 4. Volatility-aware market structure

- production pivots use a two-candle fractal radius, widened to three in high volatility;
- strict perfect-monotonic HH/HL or LH/LL was replaced by a two-thirds material-pivot majority requiring highs and lows to agree;
- the former absolute prominence filter was removed after replay showed that it deleted legitimate crypto levels;
- raw and structural pivots remain separately observable.

### 5. Context, decision, and confirmation

- context window: up to 96 candles;
- recent decision window: 24 candles;
- event-local confirmation lookahead: 3 candles;
- candle events outside the decision window cannot create a current reversal hypothesis;
- trend structure and causally formed zones retain the preceding context.

### 6. Technical indicator confirmation

The unified context now exposes SMA20, EMA12/26, RSI14, MACD and signal, ATR14, ADX14, Bollinger bands, and volume-weighted average price. Indicator votes cannot select a regime alone. They confirm a book/structure hypothesis or decision-window directional progress.

An unresolved range breakout attempt remains `PENDING`; indicator and price progress cannot prematurely convert it into a directional regime.

### 7. Multi-timeframe contract

`run_multi_timeframe_engine_trend` accepts preloaded candle arrays by interval and preserves the requested decision timeframe. Higher intervals may confirm it or force `UNKNOWN` on directional conflict, but may not promote an `UNKNOWN` lower-timeframe decision into a trade direction.

### 8. Visualization

Explicitly out of scope by user decision. No plot or chart renderer was added.

### 9. Balanced out-of-sample validation

- 60 raw replay rows deduplicated to 45 market periods;
- balanced UP/DOWN/FLAT subset: 27;
- chronological train/test split: 18/9;
- OOS opposite-direction errors: 0;
- safety violations: 0;
- deterministic-proxy OOS exact match: 4/9;
- deterministic-proxy OOS abstentions: 3/9;
- independent manual OOS labels: 0/9.

The validation implementation is complete, but market-validity acceptance is correctly `BLOCKED_MANUAL_LABELS`. The generated manual-label template contains no engine predictions and must be completed by a reviewer who has not seen the replay answers.

## Hardened replay

Final raw regime counts:

- UP: 18
- DOWN: 10
- FLAT: 10
- UNKNOWN: 22

Three raw `MISMATCH` rows are `EXPECTED_FLAT → UP`. Two rows are aliases for the same market period with bullish structure and bullish indicators. The third has a confirmed bullish reversal. These are manual-review label conflicts, not opposite directional failures.

## Final-answer contract

Every JSON result exposes:

- one `market_regime`;
- `final_answer.is_conclusive` and `is_abstention`;
- selected confirmed hypothesis when one exists;
- exact fallback reason when the answer is `UNKNOWN`;
- analysis window, indicator context, and all hypothesis lifecycle states.

The standalone payload version is `engine_trend_preview_v2`.

## Decision

**PASS for technical implementation and continued research use.**

**HOLD for production market-validity acceptance until blind manual OOS labels are supplied.**
