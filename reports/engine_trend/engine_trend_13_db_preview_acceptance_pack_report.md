# ENGINE-TREND-13 — Engine Trend DB Preview Acceptance Pack

## Stage goal

Package the confirmed ENGINE-TREND-12 real-DB CLI preview into stable, checksum-protected, offline-verifiable acceptance evidence without changing engine behavior.

## Baseline

The stage starts from `5044345`, following storage discovery (`54800af`), adapter implementation (`fb63c22`), successful operational smoke (`1e244da`), and DB CLI preview (`247ff0f`). The confirmed source is PostgreSQL 16.10, container `traders-ml-postgres-1`, host port 5433, volume `traders_ml_traders_ml_postgres_data`, table `public.market_candles`.

## Files created/changed

- `reports/engine_trend/acceptance_pack/ENGINE_TREND_13_ACCEPTANCE_PACK.md`
- `reports/engine_trend/acceptance_pack/ENGINE_TREND_13_COMMANDS.md`
- `reports/engine_trend/acceptance_pack/ENGINE_TREND_13_ARTIFACT_MANIFEST.json`
- `reports/engine_trend/acceptance_pack/ENGINE_TREND_13_SAFETY_CHECKLIST.md`
- `tests/test_engine_trend_13_acceptance_pack.py`
- this report

No file under `app/market_reader/engine_trend/` was changed.

## Acceptance artifacts used

The six committed files under `reports/engine_trend/db_cli_preview/` are used: one preview and one full result for each of BTCUSDT, ETHUSDT, and SOLUSDT. They are evidence/output only, not candle inputs or mocks.

## Manifest summary

The manifest records the confirmed source metadata, supported inputs, availability counts, per-symbol outcomes, artifact paths and SHA256 checksums, and explicit negative trading claims. It stores no DB URL, password, or environment value.

## Per-symbol results

| Symbol | Interval | Loaded | Boundary | Regime | Confidence | W/E | Safety | Preview SHA | Result SHA |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |
| BTCUSDT | 15m | 96 | READY | UNKNOWN | 0.3 | 0/0 | NOT_EVALUATED; safe=false; live=false | `a552f2015754` | `acef41aaa7bc` |
| ETHUSDT | 15m | 96 | READY | UNKNOWN | 0.3 | 0/0 | NOT_EVALUATED; safe=false; live=false | `27c2d9839143` | `8bcc8c132b68` |
| SOLUSDT | 15m | 96 | READY | UNKNOWN | 0.3 | 0/0 | NOT_EVALUATED; safe=false; live=false | `896debe7eed9` | `f24ce1d6d08f` |

Artifact paths are the lowercase `{symbol}_15m_preview.json` and `{symbol}_15m_result.json` paths recorded in the manifest.

## Safety contract verification

All artifacts retain `trade_signal = NOT_EVALUATED`, `safe_for_runtime_trading = false`, and `live_trading_connected = false`. No trading action, execution connection, DB write behavior, old L1/L2 import, credential, or edge claim was added. `engine_trend` remains a preview/context component and is not a trading system.

## Commands documented

The commands document provides the canonical availability command and 96-candle PowerShell invocation for every accepted symbol. It lists allowed environment-variable names without values and warns against committing the real DB URL.

## Tests executed

- `python -m pytest tests\test_engine_trend_13_acceptance_pack.py` — 5 passed.
- ENGINE-TREND-10 and ENGINE-TREND-12 adapter/CLI tests — 17 passed.
- Relevant ENGINE-TREND-01 through ENGINE-TREND-13 suite — 215 passed.

Full pytest was intentionally not used as a gate because of the known unrelated empty-data `StatisticsError` in `app/diagnostics/solusdt_sidecar_calibration_replay.py`.

## Scans executed

- write SQL scan — no matches; no executable write SQL.
- old L1/L2 import scan — no matches in the acceptance test.
- trading/runtime scan — matches only in the safety checklist and no-claims prose; descriptive safety references only, no trading action logic.
- secrets scan — no URL scheme, password token, or environment assignment matches in the acceptance pack; allowed environment-variable names are documented without values.

## What this stage proves

The committed DB CLI evidence can be located and integrity-checked offline; its source and commands are documented; the provider boundary was `READY`; safe engine results and JSON outputs were produced; and the fail-closed safety contract is preserved.

## What this stage does not prove

It proves no trading edge, profitability, predictive power, model-training validity, runtime-trading readiness, 1h/4h behavior, additional symbols, or behavior outside the committed acceptance windows.

## Known limitations

Coverage is limited to one 96-candle 15m evidence window for each of three symbols. All accepted regimes are `UNKNOWN` at confidence 0.3. The known unrelated full-suite diagnostic failure remains out of scope.

## Next recommended stage

ENGINE-TREND-14 — Engine Trend Known Limitations and Next Decision Gate, to choose among expanding inputs/windows, investigating `UNKNOWN` confidence behavior, or stopping core work, without trading claims or runtime trading.
