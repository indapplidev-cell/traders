# ENGINE-TREND-14 — Known Limitations

## Current confirmed capabilities

The read-only PostgreSQL adapter can load confirmed `public.market_candles` data through the provider boundary. The DB CLI produced JSON results for BTCUSDT, ETHUSDT, and SOLUSDT at `15m`, loading 96 candles per symbol with boundary status `READY`, zero warnings, and zero errors. The safety fields remained fail-closed.

## Current accepted baseline

ENGINE-TREND-13 freezes six checksum-verified real-DB artifacts. Every accepted result is `UNKNOWN` with confidence `0.3`. This baseline proves the data-to-result pipeline and artifact integrity; it does not establish market-reading quality.

## Known limitations

1. Only one short latest-window preview of 96 candles was checked per symbol.
2. Only BTCUSDT, ETHUSDT, and SOLUSDT were checked.
3. Only the `15m` interval was checked; `1h` and `4h` were absent in the latest audit.
4. All acceptance results were `UNKNOWN` with confidence `0.3`.
5. There are no labeled historical UP, DOWN, or FLAT windows.
6. There is no visual/manual benchmark for comparison.
7. There is no validation matrix across market regimes.
8. There are no false UNKNOWN, false UP, false DOWN, or false FLAT statistics.
9. Different window lengths and historical regimes have not been evaluated.
10. Confidence stability has not been evaluated.
11. The acceptance pack validates the pipeline, not market-reading accuracy.
12. The preserved safety contract is not trading readiness.
13. No trading edge is claimed.

## UNKNOWN 0.3 interpretation

The current result may mean that the selected window supplied insufficient directional evidence, conservative composer rules operated as designed, evidence conflict or low effective coverage caused a safe fallback, or the latest 96 candles were weak/noisy. It is also possible that current thresholds are conservative, but this sample cannot establish that.

The committed result traces include conservative-fallback reason codes. That is evidence of the selected path, not evidence that the classification is correct. `UNKNOWN 0.3` proves neither that the core is poor nor that it is good, is not established as a bug, and does not prove absence of a trend.

**UNKNOWN 0.3 is a safe baseline result that requires historical regime validation before changing the core logic.**

## Data limitations

Coverage is restricted to three symbols, one interval, and one latest window per symbol. The prior audit did not establish `1h` or `4h` availability. Committed report JSON is output evidence only and must never be used as a candle source.

## Evaluation limitations

No independent reference labels, regime-balanced sampling, reviewer agreement process, window-length comparison, confidence distribution, or classification error matrix exists yet. Profitability and predictive power have not been evaluated and are outside this gate.

## Architecture limitations

The current evidence exercises the established adapter, boundary, evidence matrix, composer, and facade as one pipeline. It does not isolate which component explains a classification, nor justify changing Nison, Altunina, Schwager, BookEvidenceMatrix, RegimeComposer, OHLC integrity, schemas, adapter, or CLI behavior.

## Safety limitations

Outputs remain descriptive market context: trade evaluation is disabled, runtime trading is unsafe, and live execution is disconnected. These restrictions prevent operational use; they do not certify accuracy or readiness.

## What must not be inferred

- The engine is correct or incorrect.
- `UNKNOWN 0.3` is a defect or proof of no trend.
- The engine has edge, predictive power, profitability, or trading readiness.
- Threshold tuning is justified by the latest-window sample.
- Results generalize to other symbols, intervals, window sizes, or historical regimes.

## Required next evidence

A frozen historical validation pack must compare engine output with manual reference labels on at least nine `15m` windows across BTCUSDT, ETHUSDT, and SOLUSDT. It must cover clear UP, DOWN, FLAT/range, and unclear/mixed contexts, retain reason codes and confidence, distinguish acceptable from questionable UNKNOWN results, and make no core changes during evidence collection.
