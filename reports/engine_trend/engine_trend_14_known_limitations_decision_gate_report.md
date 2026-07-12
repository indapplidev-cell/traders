# ENGINE-TREND-14 — Engine Trend Known Limitations and Next Decision Gate

## Stage goal

Record what the existing DB preview proves and does not prove, interpret the `UNKNOWN 0.3` baseline conservatively, select the next evidence gate, and define ENGINE-TREND-15 without changing engine behavior.

## Baseline

The stage starts from commit `d264d57`. ENGINE-TREND-09 through ENGINE-TREND-13 confirmed the PostgreSQL read source, adapter, operational smoke, DB CLI preview, six real artifacts, and offline acceptance pack. The accepted scope is BTCUSDT, ETHUSDT, and SOLUSDT at `15m`, 96 candles each, boundary `READY`, regime `UNKNOWN`, confidence `0.3`, and zero warnings/errors.

## Files created/changed

- `reports/engine_trend/decision_gate/ENGINE_TREND_14_KNOWN_LIMITATIONS.md`
- `reports/engine_trend/decision_gate/ENGINE_TREND_14_DECISION_GATE.md`
- `reports/engine_trend/decision_gate/ENGINE_TREND_14_VALIDATION_PLAN.md`
- `reports/engine_trend/decision_gate/ENGINE_TREND_14_DECISION_RECORD.json`
- `tests/test_engine_trend_14_decision_gate.py`
- this report

No file under `app/market_reader/engine_trend/` was changed.

## Inputs reviewed

All requested ENGINE-TREND-09 through ENGINE-TREND-13 stage reports, the four acceptance-pack files, and all six DB CLI preview/result artifacts were present and reviewed. No requested input artifact was missing.

## Known limitations summary

Acceptance covers only one latest 96-candle window for each of three symbols at `15m`; the latest audit did not establish `1h` or `4h`. There are no frozen manual labels, regime-balanced historical windows, comparison benchmark, error statistics, window-length comparison, historical-regime coverage, or confidence-stability evidence. The acceptance pack proves the pipeline, not market-reading quality.

## UNKNOWN 0.3 interpretation

The result is consistent with a conservative fallback recorded in the decision trace. Possible explanations include insufficient directional evidence, conservative composition, effective conflict/coverage constraints, or a weak/noisy latest window. Conservative thresholds remain a hypothesis, not a conclusion. `UNKNOWN 0.3` proves neither correctness nor failure and is not established as a bug or proof that no trend existed.

**UNKNOWN 0.3 is a safe baseline result that requires historical regime validation before changing the core logic.**

## Decision options

Options considered were: stop at the CLI baseline (A), tune immediately due to UNKNOWN (B), validate historical windows before core changes (C), or expand symbols/intervals first (D). Option B was explicitly rejected because the unlabelled latest-window sample cannot justify tuning.

## Selected decision

**Option C — Build historical validation pack before changing core.**

## Validation plan summary

ENGINE-TREND-15 will freeze at least three `15m`, 96-candle windows per symbol (minimum 9; target 15) across clear UP, DOWN, FLAT/range, unclear/choppy, breakout/fakeout, and latest contexts where available. Manual labels are references only. The comparison records regime, confidence, reasons, diagnostics, match status, and notes. No core tuning occurs in that stage.

## Tests executed

- `python -m pytest tests\test_engine_trend_14_decision_gate.py` — 5 passed.
- `python -m pytest tests\test_engine_trend_13_acceptance_pack.py` — 5 passed.
- ENGINE-TREND-10 adapter plus ENGINE-TREND-12 DB CLI tests — 17 passed.
- Relevant ENGINE-TREND-01 through ENGINE-TREND-14 suite — 220 passed.

Full pytest is intentionally not an acceptance gate because of the unrelated existing empty-data `StatisticsError` in `app/diagnostics/solusdt_sidecar_calibration_replay.py`.

## Scans executed

- write SQL scan: no matches; no executable write SQL.
- old L1/L2 scan: no matches; no imports.
- trading scan: two descriptive safety/non-goal references only, no trading action logic.
- secret scan: no matches for URL schemes, password tokens, credential-variable assignments, or values.
- diff review: no real connection URL, credential, environment value, or change under `app/market_reader/engine_trend/`.

## What this stage proves

The project has an explicit, machine-readable decision to preserve the current core and collect historical validation evidence next. It defines a reproducible first quality-check scope and separates pipeline acceptance from market-reading evaluation.

## What this stage does not prove

It does not prove classification accuracy, absence or presence of trend, generalization, predictive power, edge, profitability, trading readiness, or a need to tune. It adds no historical validation results and makes no runtime or execution connection.

## Known limitations

The decision inherits the current three-symbol, `15m`, latest-window baseline. Manual labeling contains judgment and must retain ambiguity and reviewer notes. ENGINE-TREND-15 must establish the first comparative evidence before any tuning decision.

## Next recommended stage

**ENGINE-TREND-15 — Historical Market Reading Validation Pack.** It must collect validation evidence without changing core logic; any tuning proposal belongs to a later, separate decision stage.
