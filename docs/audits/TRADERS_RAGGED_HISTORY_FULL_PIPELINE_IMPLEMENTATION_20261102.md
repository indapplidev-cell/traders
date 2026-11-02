# Ragged-history full-pipeline calibration implementation

Date: 2026-11-02
Scope: read-only LONG scalping research
Production mutation: none
LIVE: disabled

## Result

The full-pipeline calibration control plane now accepts different causal
history depths for the 20-symbol universe. A late history start or an isolated
gap is recorded as `PARTIAL_COVERAGE`; it no longer blocks every symbol.

The first real V2 freeze completed with:

- status: `FROZEN`;
- dataset hash: `f820eb6809d74726494740010432cf49d3dd69896f5af4a1dc780cad5c80db89`;
- usable symbols: 20 of 20;
- partial-coverage symbols: 20 of 20;
- blocking reasons: none;
- observed historical cost rows: 1,803;
- cost-evidence interval: `1788385800000..1793485500000`;
- earlier costs: explicitly `MODELLED_CONSERVATIVE`.

Examples of post-warmup causal starts are ETHUSDT `1761271200000`,
SOLUSDT `1761902100000`, BTCUSDT `1764939600000`, the mid-depth cohort
`1786281660000`, and the shortest cohort `1790007660000`. No symbol is
silently projected back to July 2025.

## Implementation

- `FullPipelineCalibrationRequestV2`, `RaggedDatasetManifestV2`, per-symbol
  segments, fold participation and checksums were added.
- Coverage is intersected across 1m/5m/15m/1h after timeframe-specific warmup.
- Gaps split history into causal segments rather than invalidating the entire
  dataset.
- `HistoricalCostModelV1` uses observed symbol/regime and symbol buckets with a
  global conservative fallback. Fees have a 10 bps per-side floor and reserve
  has a 3 bps floor.
- `FullPipelineReplayEngineV1` evaluates production-derived opportunities in a
  shared chronological portfolio.
- Baseline reconstruction reuses persisted production decisions first and
  invokes the native `PipelineRunner` only where historical decisions do not
  exist.
- Baseline output is checkpointed every 100 boundaries and truncates an
  uncommitted JSONL tail on resume.
- Training performs sensitivity plus deterministic one-worker TPE, freezes
  finalists before opening the locked holdout, and allows holdout only to
  reject rather than retune a candidate.
- Strategy-score and minimum-net-edge thresholds are now enforced by the
  historical end-to-end gate instead of being inert replay parameters.

## Current execution state

The real baseline reconstruction was started against the frozen V2 dataset.
It is resumable and was proven to advance through the pre-persisted candle
history. It is not yet complete at this snapshot; therefore no universal
weights, candidate, PAPER canary or profitability claim exists yet.

The research implementation does not update the active YAML, production
database, PAPER selector, Docker services, or LIVE authority.

## Verification

- focused full-pipeline/ragged/replay/reconstruction/search suite: 37 passed
  (including 6 ragged/resume tests);
- Python compile: passed;
- real V2 freeze: passed;
- production mutations: zero.

## Next gate

Allow the resumable baseline to finish all 20 symbols, run the deterministic
search, freeze finalists, open the internal holdout once, and independently
verify trades and accounting. PAPER canary remains blocked unless every
economic and stability gate passes.
