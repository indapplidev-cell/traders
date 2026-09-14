# Result-driven parameter sweep — block 02

FINAL_VERDICT = BLOCKED_DATA
BLOCK_PASS = false

Implemented bounded read-only HistoryProvider: four closed-candle timeframes,
per-timeframe warmup, search interval and exit tail; all persisted pipeline
boundaries independent of setup status or PAPER positions; immutable output
paths; byte/row ceilings; content and manifest fingerprints; gap, duplicate,
OHLC validity and causal-window checks; exact missing-input diagnostics.
The CLI exposes the provider via --result-search-freeze-history and exits 2 for
BLOCKED_DATA while preserving evidence. No production writes or live substitutions.

Actual acceptance: all 10 current universe symbols, 2026-09-13 19:00–23:00 UTC,
200 warmup candles per timeframe and exit tail through 2026-09-14 00:00 UTC.
11,850 candles plus 480 persisted boundaries, 12,330 records, 6,165,973 bytes.
Candles: no gaps, duplicates, invalid OHLC, missing warmup/tail or future rows.
Derived historical cost fields present on 161/480 boundaries; missing on 319.
Raw bid/ask depth ladders: 0/480. This is not a claim that every conceivable
historical interval or external archive was exhausted.

Concrete blocker: the existing configured sources cannot support arbitrary
recomputed early-stage entries throughout this period with HISTORICAL_VERIFIED
execution inputs. The runtime cost source estimates depth for reference_notional
/ entry, and persists derived VWAP/cost diagnostics instead of full depth ladders.
Those derived snapshots may support their original input/quantity, but do not
prove another entry price/quantity. On most boundaries even these inputs were
not evaluated. Restricting to formerly admitted setups or supplying current books
would not meet the requested history-wide recomputation contract.

Corroboration: current public schema has no separate historical book/commission
snapshot tables; scalping_shadow.py retains bid/ask/VWAP/reference_quantity fields
but no depth arrays; scalping_paper_runner.py loads live REST book/depth and current
commission authority. historical_reconstruction.py already exposes unavailable
historical cost sources explicitly. Source code observations were checked against
fresh actual DB extraction, not accepted from old reports alone.

BTCUSDT has zero old PAPER positions, yet acquired 1,185 candles and 48 boundaries.
Missing old positions did not block history. Existing PAPER data was not replayed
or filtered into a claimed new trade. No search trials or profitable finds exist.

Limitations: engine-specific warmup certification, historical commission/depth
and as-of probability authority integration, assumption-based execution, optional
independent-evaluation splitting and full lifecycle support are not completed.
The provider never labels this incomplete dataset HISTORICAL_VERIFIED. No PASS
is claimed merely because engineering tests and a fail-closed smoke pass.

Tests: history+contract 33 passed; committed history+contract+CLI/GUI v2 35 passed;
compile and diff check passed. Fresh separate reload verified the same dataset
fingerprint. This is dataset reproduction, NOT independent trade replay.

Deployment source = 6d555c521a179da929375526b29534950300500a
Method = direct checkout D:/disk_E/game_projects/traders/traders-ml
Interpreter = C:/Program Files/Python311/python.exe
Fresh diagnostics PID = 6672, module_dirty=false
History module SHA256 = d5ae924a12417d8d7b64009211e57e3a88073a7b36ccbbd0f3fc514b7650101a
Fresh installed CLI actual-data smoke exit = 2, BLOCKED_DATA (expected).
Deployment of acquisition is verified; full block acceptance remains BLOCKED.
No production component was changed or restarted.

Local dataset = artifacts/result_search_refactor/block02/dataset_universe_committed
Content SHA256 = 51bb20a3783eb2f54e2ec0b68e873072cb4cf89cc3e978580ed4b5e3fb207385
Dataset fingerprint = f368b03cb32d88658c171213a5deb2f69a207e761c3d9dcd5f86acc56920f346
Request = artifacts/result_search_refactor/block02/request_global.json
Tracked manifest = docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_02_MANIFEST.json
Reproduce extraction into a NEW directory with the documented CLI request flag.
Reload original data with HistoryProvider.load(Path(local_dataset)) to verify
content/manifest identity. Mutable DB re-extraction is not promised identical.
Large history files are local only; no credentials were saved or committed.

FILES_CHANGED = traders_ml/parameter_sweep/search_history.py;
traders_ml/parameter_sweep/cli.py; tests/research/test_result_search_history.py;
docs/research/scalping_v2_parameter_sweep.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_01_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_02_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_02_MANIFEST.json;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_03_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_04_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_05_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_06_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_07_FINAL.md; online_trader.md

Project-state evidence commit: git log -1 --format=%H -- this file.
Documentation commit: git log -1 --format=%H -- online_trader.md.
Final push and fresh remote identity are recorded in the task handoff.
Next stage: supply historical causal inputs and complete block 02; do not start
block 03 before BLOCK_02_PASS. Primary project ACK owner blocker is unchanged.
