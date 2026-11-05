# Full-pipeline v3 implementation checkpoint — 2026-11-05

## Verified state

- The frozen request and dataset remain V2 with dataset hash `f820eb6809d74726494740010432cf49d3dd69896f5af4a1dc780cad5c80db89`.
- Baseline v2 remains a diagnostic reference: 20 symbols, 592,196 decision traces, 981 simulated trades, net PnL −419.14449 on starting equity 1,000. Its costs are aggregated incorrectly for v3 accounting.
- A v3 feature-cache command now evaluates the native `PipelineRunner` on every pre-holdout 5m boundary, including early rejections. It stores all six stage payloads, statuses, the first rejection, four closed-candle references and a decision hash. Candle inputs are serialized once per symbol/segment in a separate checked partition. Checkpoints are written every 100 boundaries; resume truncates an uncommitted tail.
- The cache builder clips source candle reads at the start of the locked internal holdout. Its manifest stays `IN_PROGRESS` before that holdout is opened. No v3 training candidate or profitable weights are yet verified.
- `HistoricalCostLedgerV3` stores each fee, spread, slippage, depth impact and reserve independently and rejects future cost evidence or an unreconciled net PnL. `resolve_research_parameter_set_v3` constructs an isolated native parameter set and rejects unsupported cost changes and safety cap violations.
- An initial read-only smoke run processed three ADAUSDT boundaries with closed 1m/5m/15m/1h references and demonstrated checkpoint resume. A background cache pass was started for the remaining pre-holdout boundaries; progress is not evidence of training completion.
- Relevant tests: 17 passed; new v3 files pass Ruff and compile.

## Open implementation work

1. Finish the pre-holdout cache and verify its boundary counts and partition checksums. The frozen manifest reports 592,193 5m rows whereas baseline v2 emitted 592,196 boundaries; BTCUSDT, ETHUSDT and SOLUSDT each account for one extra v2 boundary. This difference must be reconciled before parity can pass.
2. Implement candidate-specific native reruns using the candle archive and parameter block hashes. The current v3 code supplies the isolated parameter resolver but does not yet run candidate trials or model the full position lifecycle.
3. Connect explicit v3 ledgers to portfolio fills and exits, then reproduce the baseline and explain the PnL difference from v2.
4. Implement stage activity, causal train/validation search, immutable finalist freeze, one-time holdout, verifier and acceptance gates. Keep PAPER/LIVE unchanged.

The implementation is **partial**. No v3 baseline parity, training result, verifier PASS or activation is claimed.

## Cache storage correction

The initial full cache pass was stopped after ADAUSDT reached 16,400 boundaries: each record repeated a roughly 120 KB frozen parameter snapshot in five stage payloads. The partial feature file reached about 10.3 GB, which would have exhausted the research disk before all symbols completed. Native payload compaction now retains that snapshot by configuration hash and removes duplicate analysis context from the setup record. A smoke record fell from about 655 KB to 37 KB while preserving the unique module and stage evidence. Five v3 tests passed. The oversized partial artifact is retained for forensic comparison because automated deletion was rejected; the corrected pass uses a new output directory and does not treat the old checkpoint as compatible.
