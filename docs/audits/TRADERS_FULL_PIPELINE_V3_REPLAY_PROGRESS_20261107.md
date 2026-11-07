# Full-pipeline v3 research progress — 2026-11-07

## Verified inputs

- Frozen request and dataset V2 remain unchanged; dataset SHA-256 identity is `f820eb6809d74726494740010432cf49d3dd69896f5af4a1dc780cad5c80db89`.
- The compact v3 pre-holdout cache has 20 certified partitions and 534,596 boundaries. Its `holdout_evaluated` field is false. The 22–31 October rows were not opened in this task.
- The frozen manifest's 592,193 `rows_5m` total undercounts three aligned first boundaries. BTCUSDT, ETHUSDT and SOLUSDT start on exact 5m boundaries; the old floor-of-duration count loses one each. Their baseline and cache first boundary IDs equal the manifest segment start. Counting aligned boundaries in `[start_ms, end_ms)` gives 592,196, equal to baseline v2. The frozen manifest was not rewritten; future freezes use the corrected count.
- Baseline v2 remains diagnostic: 981 simulated trades, net PnL −419.14449. It is not a list of candidate entries.

## Cost isolation

The V2 aggregate cost model was fit through the dataset end and is unsuitable for v3 search because that interval includes validation and locked holdout dates. A separate v3 cost model was built from 963 production observations strictly before the final validation start (12 October), excluding all earlier validation windows in the SQL query. Its model hash is `1678bc194cf8b2972a9991a99e03ffb2a2d76adafe8c75d1e5f8f973b24b7174`; its receipt records `holdout_evaluated=false`. Candidate native reruns now require this model and reject the V2 aggregate model. Aggregate bucket costs are labelled `MODELLED_CONSERVATIVE`, not timestamped `OBSERVED` snapshots.

## Implemented, not yet accepted

- A research-only portfolio lifecycle core orders symbols together, applies shared slots and capital limits, admits fills only after the signal, gives stop priority when stop and target touch the same candle, expires pending entries, clips the role end and creates per-trade `HistoricalCostLedgerV3` records.
- Native candidate stage decisions can be checkpointed as compact signal shards. A new CLI action processes the certified pre-holdout cache sequentially with one worker; it records all stage statuses, first rejection and decision hash, and stores execution inputs only for ready plans.
- A shard replay reader merges candidate signals and frozen 1m candles by global event time and validates source hashes. The current result is explicitly `REPLAY_NOT_VERIFIED` and `eligible_for_training=false`.
- The shard reader now also carries closed 5m context and calls the native `analyze_position_exit` on positions after fill, with stop/target evaluated first. Missing causal context yields `DATA_UNAVAILABLE` rather than a fabricated exit. This integration has only synthetic focused-test coverage; full-history parity is pending.
- Focused tests: 22 passed. Ruff passes on changed v3 modules and focused tests. The legacy `full_pipeline.py` still has unrelated pre-existing Ruff findings; it compiles.

## Remaining gates

The position lifecycle is not yet an accepted full replay. Candidate stage decisions must be regenerated and compared to baseline, native analytical exits require full-history parity, actual observed timestamped execution costs must be separated from modelled fallback when available, and the independent verifier must reproduce the trades. Parameter activity, block-hash reuse, train/validation search, immutable finalist freeze and one-shot holdout are still pending. Old `train_ragged` remains prohibited for v3. No profitable weights or PAPER readiness are claimed.
