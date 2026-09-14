# Result-driven parameter sweep — block 02

FINAL_VERDICT = HISTORY_ACCEPTANCE_PASS
BLOCK_PASS = conditional on final documentation/push gate recorded in task handoff

This report supersedes the original blanket cost blocker and the later requirement
for an exact historical filesystem membership ledger. Neither is a prerequisite
for the requested causal historical provider. It does not certify arbitrary
combinations with missing required market inputs.

| Requirement | Verified result |
| --- | --- |
| Real symbol history, independent of old positions/setups | All 10 symbols; 11,850 candles and 480 unfiltered boundaries; BTCUSDT has zero PAPER positions |
| Authoritative warmup | 200 bars each timeframe; required windows 1m=60, 5m=120, 15m=64, 1h=50; insufficient request rejected |
| Read-only source | Protected database binding; transaction_read_only=on; Alembic 0031_scalping_parameter_sets |
| Frozen identities | Schema 3, content/statistics checksums, manifest fingerprint, source tables, configuration epochs and coverage |
| Causal statistics | Production hierarchy builder; completed outcomes filtered before each decision; future/undated outcomes excluded |
| Outcome provenance | 4,619 archive records checked against closed candle paths; four incomplete paths excluded; 643 compatible prospective outcomes plus 53 PAPER outcomes, filtered by parameter set |
| Quality | HISTORICAL_VERIFIED is scoped to checked closed market history and event-time statistics; ASSUMPTION_BASED remains distinct; required costs checked per combination |
| Intervals | Warmup/search/exit tail and optional independent evaluation/exit tail; overlap rejected before extraction; search view excludes exit and independent data |
| Diagnostics | Missing candles/tail, duplicates, invalid OHLC, budgets, tampering and missing required snapshots have explicit failures |
| Fresh installed acceptance | PASS, PID 6140, direct checkout, Python 3.11, clean committed source |

Main real interval: 2026-09-13 19:00–23:00 UTC, exit tail through
2026-09-14 00:00 UTC. No claim of 30 days of supported history.
Independent split acceptance uses BTCUSDT: search 19:00–20:00, exit tail
20:00–21:00, evaluation 21:00–23:00, evaluation exit tail 23:00–00:00 UTC.
There are no candle gaps, duplicates or truncated tails in these acquisitions.

Statistics availability means recorded completed event time validated against the
candles determining the outcome, not the exact instant a production reader saw
an appended file. This is an explicit research event-time contract. No current
live market value is substituted; no assumed probability is invented.

28 evaluations contain a separate baseline and the 27-value grid (one equivalent
baseline): 18 of the 27 grid configurations have all admission rejections verified;
nine require unavailable cost snapshots on 23 newly reached boundaries. Baseline
parity remains 480/480. This is admission-prefix evidence, not a completed trade
simulator. Raw depth is still unavailable; arbitrary entry/quantity changes cannot
reuse incompatible derived costs. Block 03 must preserve these requirements.

Tests: 69 passed (history, statistics, applicability, search contract and production
statistics); compile PASS; diff check PASS. A separate fresh process reloaded the
committed acceptance dataset and verified its fingerprint.

Deployment source = 2e3e2ffe1252aa741a62420d726bcf19bb8c3cc0
Implementation source = 5b7d9335e789bd53e1eb69305a96855d9c9ae83d
Checkout = D:/disk_E/game_projects/traders/traders-ml
Interpreter = C:/Program Files/Python311/python.exe
Dataset = artifacts/result_search_block02_committed_acceptance_v2/dataset
Fingerprint = a890247e7f011691c1a50344a72edd1354907ff72f7f7748237d6fdc40989a72
Evidence = TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_02_ACCEPTANCE.json
Trading YAML SHA256 = 70bba34921cdfb49709771068dd1ca53641dd4e9811ebd50046ef5aaf4989499
Safety = no production mutations, restarts, order actions or LIVE activation.

Reproduce in a new output directory:
`python -m scripts.result_search_history_acceptance --output artifacts/block02_new_acceptance`
The script uses the existing local request and combinations; copies are retained
in BLOCK_02_REQUEST.json and BLOCK_02_COMBINATIONS.json beside this report.
Mutable source extraction may have a different fingerprint; frozen reload must match.
Large datasets and archive contents are local only.

FILES_CHANGED = traders_ml/parameter_sweep/cli.py;
traders_ml/parameter_sweep/historical_statistics.py;
traders_ml/parameter_sweep/history_applicability.py;
traders_ml/parameter_sweep/search_history.py;
tests/research/test_historical_statistics.py; tests/research/test_result_search_history.py;
scripts/result_search_history_acceptance.py; docs/research/scalping_v2_parameter_sweep.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_02_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_02_ACCEPTANCE.json;
docs/audits/BLOCK_02_REQUEST.json; docs/audits/BLOCK_02_COMBINATIONS.json; online_trader.md.

Project-state evidence commit: git log -1 --format=%H -- this report.
Documentation commit: git log -1 --format=%H -- online_trader.md.
Final remote verification is performed after the documentation commit; transport
values belong to the final handoff. Next stage: BLOCK 03 full chronological
shared simulator. Primary ACK owner blocker and module percentages are unchanged.
