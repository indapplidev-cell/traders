# ENGINE-TREND-15B — Symbol Suitability and Expanded Historical Validation

## Stage goal
Determine validation-symbol suitability and expand historical coverage without core tuning.
## Baseline
ENGINE-TREND-15: 15 safe real windows; all UNKNOWN 0.3.
## Files created/changed
Runner, offline test, availability/suitability/window/matrix artifacts, 90 per-window artifacts, summary, manifest, and this report. Protected modules unchanged.
## DB source
Read-only PostgreSQL `public.market_candles`.
## Symbol availability discovery
Only BTCUSDT, ETHUSDT, SOLUSDT at 15m; approximately 50,962 candles each.
## Suitability scoring
OHLC-only non-overlapping 96-candle samples; no engine-output leakage and no threshold relaxation.
## Selected symbols
All three: highest-ranked asset is main candidate, remaining non-BTC asset secondary, BTC macro/noisy benchmark.
## Expanded validation scope
45 windows; 15 per symbol; five required window types where available.
## Expanded validation result summary
Regimes {'UNKNOWN': 45}; statuses {'QUESTIONABLE_UNKNOWN': 30, 'MATCH': 9, 'ACCEPTABLE_UNKNOWN': 6}.
## Per-symbol summary
{'BTCUSDT': {'UNKNOWN': 15}, 'ETHUSDT': {'UNKNOWN': 15}, 'SOLUSDT': {'UNKNOWN': 15}}
## Per-label summary
{'EXPECTED_DOWN': {'QUESTIONABLE_UNKNOWN': 9}, 'EXPECTED_FLAT': {'QUESTIONABLE_UNKNOWN': 9}, 'EXPECTED_UNKNOWN_OR_MIXED': {'MATCH': 9}, 'EXPECTED_UP': {'QUESTIONABLE_UNKNOWN': 12}, 'HIGH_VOLATILITY_CHOP': {'ACCEPTABLE_UNKNOWN': 3}, 'RECENT_BASELINE': {'ACCEPTABLE_UNKNOWN': 3}}
## Safety contract verification
45/45 passed; zero violations.
## Tests executed
Real PostgreSQL runner completed with 45 windows. Runner compilation passed. The focused acceptance/adapter group passed 35/35 tests. The complete requested ENGINE-TREND-01 through ENGINE-TREND-15B suite passed 228/228 tests. Full pytest was intentionally not used because of the known unrelated diagnostics `StatisticsError`.
## Scans executed
Write-SQL, legacy, trading-term, artifact-secret, diff, and protected-core scans were executed. Matches were reviewed as descriptive safety/prohibition references only; no executable write SQL, legacy import, trading action logic, secret, or protected-core change was found.
## Known limitations
Rule labels are validation references, not ground truth. Selection is deterministic, not a random holdout. Only three DB symbols exist. Context length remains 96; 192/384 is untested. No core tracing or tuning was performed.
## Next recommended stage
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision; no runtime trading.
