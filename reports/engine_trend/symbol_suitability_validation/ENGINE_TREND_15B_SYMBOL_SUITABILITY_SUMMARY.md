# ENGINE-TREND-15B — Symbol Suitability and Expanded Historical Validation Summary

## Purpose
Assess symbol suitability and expand real historical validation without changing engine core.
## Baseline
ENGINE-TREND-15 returned UNKNOWN 0.3 on all 15 windows.
## Data source
Read-only `public.market_candles` in PostgreSQL; report artifacts were not candle inputs.
## Symbol availability
3 symbol/interval rows discovered; only BTCUSDT, ETHUSDT, and SOLUSDT at 15m.
## Suitability scoring method
Non-overlapping 96-candle OHLC samples; score = directional×2 + flat×2 + mixed×0.5 − high-volatility chop×0.25. Engine output is excluded.
## Suitability ranking
1. BTCUSDT: score 582.5, role MACRO_NOISY_BENCHMARK
2. SOLUSDT: score 538.5, role MAIN_VALIDATION_CANDIDATE
3. ETHUSDT: score 528.75, role SECONDARY_VALIDATION_CANDIDATE
## Selected symbols
All three confirmed symbols were selected. BTC is retained as the macro/noisy benchmark, not the primary proof asset.
## Expanded validation scope
45 real windows, 15 per symbol, 96 candles each; required clean and mixed labels plus recent baseline.
## Expanded validation results
Regimes: {'UNKNOWN': 45}. Match statuses: {'QUESTIONABLE_UNKNOWN': 30, 'MATCH': 9, 'ACCEPTABLE_UNKNOWN': 6}.
## Per-symbol results
{'BTCUSDT': {'UNKNOWN': 15}, 'ETHUSDT': {'UNKNOWN': 15}, 'SOLUSDT': {'UNKNOWN': 15}}
## Per-label results
{'EXPECTED_DOWN': {'QUESTIONABLE_UNKNOWN': 9}, 'EXPECTED_FLAT': {'QUESTIONABLE_UNKNOWN': 9}, 'EXPECTED_UNKNOWN_OR_MIXED': {'MATCH': 9}, 'EXPECTED_UP': {'QUESTIONABLE_UNKNOWN': 12}, 'HIGH_VOLATILITY_CHOP': {'ACCEPTABLE_UNKNOWN': 3}, 'RECENT_BASELINE': {'ACCEPTABLE_UNKNOWN': 3}}
## Safety contract verification
All 45 rows preserve NOT_EVALUATED, runtime safety false, and live connection false; zero violations.
## Interpretation
Suitability differs descriptively, but suitability does not itself validate engine reading quality.
## Answer to key decision question
B is the leading explanation: all three symbols, including clean UP/DOWN/FLAT windows, remained UNKNOWN. Selection noise alone (A) and insufficient diversity (C) do not explain the result. D remains untested; E trace review is required before tuning.
## What this proves
The expanded real-data pipeline is reproducible and safe, and symbol/window selection can be separated from engine output.
## What this does not prove
- no trading edge proven
- no profitability proven
- no runtime trading allowed
- no execution readiness proven
- no threshold tuning performed
- no model training performed
## Recommended next stage
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision. Inspect evidence/composer traces before deciding on any change; still no runtime trading.
