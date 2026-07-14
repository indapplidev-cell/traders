# MAIN_SELECTED_ENTRY Explanation

## Frozen trade plan

- Symbol / timeframe: **BTCUSDT / 15m**
- Direction: **SHORT**
- Setup: **SHORT_DOWN_CONTINUATION_RETEST**
- Confirmation candle: `2025-12-01T13:15:00Z` (closed `2025-12-01T13:29:59.999000Z`)
- Entry: `2025-12-01T13:30:00Z` at **85994.0**
- Invalidation / stop: **86166.43 / 86215.63920478**
- Target 1: **84756.0**
- Planned RR: **5.586**
- Classification: **trend-following continuation**

## Why the entry was permissible before future candles

The 96-candle context began at `2025-11-30T13:30:00Z` and ended with the closed confirmation at `2025-12-01T13:29:59.999000Z`. The final 24 candles were the decision window. The causal chain was fixed as structure → level/retest → closed confirmation → entry → invalidation → buffered stop → pre-existing objective. Nothing after `2025-12-01T13:29:59.999000Z` participated in setup construction or ranking.

### Altunina structure reading

The last two confirmed swing highs were `[{'time': '2025-12-01T09:45:00Z', 'price': 86899.0}, {'time': '2025-12-01T10:45:00Z', 'price': 86700.0}]` and the last two confirmed swing lows were `[{'time': '2025-12-01T10:15:00Z', 'price': 86552.0}, {'time': '2025-12-01T12:45:00Z', 'price': 84756.0}]`. That is `LH/LL` structure. The bearish impulse reached `84756.0` at `2025-12-01T12:45:00Z`, followed by a `2`-bar correction. This locates the entry after a correction/rejection rather than at an arbitrary bar. Structural invalidation is `86166.43`; crossing it destroys the pullback/range-boundary premise.

### Schwager level reading

The correction tested `86196.56589459129` (nearest of EMA20/VWAP96/prior confirmed polarity level) at only `0.092` ATR distance. That zone was already visible before confirmation. The target `84756.0` is the pre-confirmation impulse extreme/range midline, never a later profitable print. In Schwager terms, the causal idea is polarity/level retest and failure to reclaim, not simply a low RSI or a candle color.

### Nison candle reading

Confirmation OHLC was `{"open": 86084.0, "high": 86148.2, "low": 85931.07, "close": 85994.0}` with body/ATR `0.274`, close location `0.290`, upper wick `0.296`, and lower wick `0.290`. It matters only because it rejected the pre-existing structural zone; the candle was not used as an isolated pattern.

### Current ENGINE-TREND and technical confirmation

The unchanged current engine replay on the 240-candle prefix returned `{"as_of_confirmation_candle": "2025-12-01T13:15:00Z", "input_candle_count": 240, "market_regime": "DOWN", "confidence": 0.72663415500723, "selected_hypothesis": "DOWN_CONTINUATION", "selected_hypothesis_status": "CONFIRMED", "selected_hypothesis_score": 0.6266341550072301, "indicator_direction": "BEARISH", "agreement_state": "ALIGNED_BEARISH", "conflict_level": "NONE", "data_quality_status": "PASS", "reason_codes": ["COMPOSER_MATRIX_READY", "COMPOSER_INPUT_VALID", "COMPOSER_CONTEXT_LINKED_HYPOTHESES_READY", "COMPOSER_DOMINANT_DOWN_CONTINUATION", "COMPOSER_DOWN_REGIME_SELECTED", "COMPOSER_NO_TRADING_ACTION"], "safety": {"trade_signal": "NOT_EVALUATED", "safe_for_runtime_trading": false, "live_trading_connected": false}, "unchanged_runtime_read_only_replay": true}`. Values from the audit scanner: `{"ema20": 86196.56589459129, "ema50": 86902.4279735881, "ema200": 89133.55659404493, "sma20": 86355.2450000003, "rsi14": 42.62640059010152, "macd": -253.66309224735596, "macd_signal": -219.68602681867267, "atr14": 328.06136521086455, "adx14": 41.06885358947959, "vwap96": 87580.73763943504, "bollinger_upper": 87212.10605353232, "bollinger_lower": 85498.38394646828, "volume_ratio_20": 0.678471262183869}`. Confirmations: `EMA20/EMA50 alignment, RSI14 side of 50, MACD versus signal`. Conflicts: `none`. Indicators were supporting/veto evidence only, never the source of the trade.

## What falsifies the setup and key risks

The premise is falsified at `86166.43` and operationally stopped at `86215.63920478`. Risks: Continuation may fail if the retest extreme is breached; Target is a prior impulse extreme and can reject price. The main analytical error could be treating a temporary correction/boundary rejection as durable while the market is actually transitioning regime, or overestimating the stability of mechanically confirmed pivots.

## After-the-fact outcome (separate phase)

- Status: **SL_BEFORE_TP**
- 24 / 48 / 96-bar labels: `SL_BEFORE_TP` / `SL_BEFORE_TP` / `SL_BEFORE_TP`
- MFE / MAE through terminal outcome: `322.24000000` / `339.28000000` (`0.3747%` / `0.3945%`)
- Bars to TP / SL: `None` / `3`
- Gross / net return: `-0.2577%` / `-0.4977%`
- Audit costs: 10 bps fee + 2 bps slippage per side = 24 bps round trip.

## Why this candidate won

It had the highest quality score (`85.1778`) using pre-entry causal context, structure clarity, level quality, confirmation quality, planned RR, conflict absence, technical agreement, and freshness. Outcomes were calculated only after `main_selected_candidate_id` was frozen.

## Top alternatives

- `ET-HED-0002` BTCUSDT SHORT at `2025-10-30T07:00:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `8.558`, pre-entry score `83.912`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0003` SOLUSDT LONG at `2025-11-15T18:45:00Z`, LONG_UP_CONTINUATION_RETEST, RR `4.096`, pre-entry score `83.597`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0004` SOLUSDT SHORT at `2025-07-12T00:15:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `4.037`, pre-entry score `83.336`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0005` BTCUSDT SHORT at `2025-07-30T21:15:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `4.738`, pre-entry score `83.310`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0006` BTCUSDT SHORT at `2025-10-10T23:15:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `8.196`, pre-entry score `83.194`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0007` SOLUSDT SHORT at `2025-10-16T11:00:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `8.029`, pre-entry score `83.159`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0008` SOLUSDT SHORT at `2025-10-22T02:30:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `4.383`, pre-entry score `83.132`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0009` BTCUSDT SHORT at `2025-10-14T11:45:00Z`, SHORT_DOWN_CONTINUATION_RETEST, RR `3.624`, pre-entry score `83.053`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
- `ET-HED-0010` BTCUSDT LONG at `2025-08-31T05:00:00Z`, LONG_UP_CONTINUATION_RETEST, RR `3.279`, pre-entry score `83.042`. Rejected as MAIN because its pre-entry score was lower; outcome was not considered.
