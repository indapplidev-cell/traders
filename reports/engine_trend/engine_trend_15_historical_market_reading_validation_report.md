# ENGINE-TREND-15 — Historical Market Reading Validation Pack

## Stage goal
Build a first real-data historical market-reading validation pack without core changes or tuning.

## Baseline
ENGINE-TREND-14 selected Option C after the accepted three-symbol DB preview baseline.

## Files created/changed
One runner, one offline test, validation JSON/CSV/Markdown artifacts, per-window previews/results, manifest, and this report. No engine core, adapter, or DB CLI file changed.

## DB source
PostgreSQL 16.10, read-only `public.market_candles`; BTCUSDT/ETHUSDT/SOLUSDT at 15m.

## Window selection method
OHLC-only deterministic rules are applied before engine execution to disjoint 96-candle blocks. No engine-output selection leakage and no threshold relaxation occurred.

## Validation scope
15 real windows, 5 per symbol, all 96 candles. UP, DOWN, FLAT, mixed, and latest types were found for every symbol; breakout/fakeout was deferred.

## Validation result summary
Statuses: {'ACCEPTABLE_UNKNOWN': 3, 'MATCH': 3, 'QUESTIONABLE_UNKNOWN': 9}. Regimes: {'UNKNOWN': 15}.

## Per-symbol summary
BTCUSDT, ETHUSDT, and SOLUSDT each contribute the same five window types.

## Per-label summary
{'EXPECTED_DOWN': 3, 'EXPECTED_FLAT': 3, 'EXPECTED_UNKNOWN_OR_MIXED': 6, 'EXPECTED_UP': 3}. RECENT_BASELINE uses the allowed provisional EXPECTED_UNKNOWN_OR_MIXED reference and is compared conservatively.

## Safety contract verification
All results: trade signal NOT_EVALUATED, runtime safety false, live connection false. Zero safety violations.

## Tests executed
- Real PostgreSQL runner: completed, 15 windows.
- Runner compilation: passed.
- Offline validation pack: 4 passed.
- ENGINE-TREND-13/14 decision and acceptance: 10 passed.
- Adapter and DB CLI: 17 passed.
- Relevant ENGINE-TREND-01 through ENGINE-TREND-15 suite: 224 passed.
- Full pytest was intentionally not used because of the known unrelated diagnostics `StatisticsError`.

## Scans executed
Write-SQL, legacy-import, trading-term, artifact-secret, diff, and protected-core scans were executed. Matches, if any, were descriptive safety/prohibition references only; no executable write SQL, legacy import, action logic, secret, or protected-core change was found.

## Known limitations
Labels are rule-based references, not ground truth. This is a small deliberately selected sample, not a random holdout or profitability backtest. Breakout/fakeout is deferred. No tuning or training occurred.

## Next recommended stage
ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision; still no runtime trading.
