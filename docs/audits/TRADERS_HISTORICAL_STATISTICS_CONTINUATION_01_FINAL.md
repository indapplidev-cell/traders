# Historical statistics continuation 01

FINAL_VERDICT = BLOCKED_FULL_SEVEN_BLOCK_ACCEPTANCE
ENGINEERING_INCREMENT = PASS_CAUSAL_STATISTICS_REPLAY

Seven-block review: block 01 foundation accepted, block 02 still lacks complete
HISTORICAL_VERIFIED acceptance, blocks 03–07 have no required sequential gates.
The last user request was executed by continuing real implementation and actual
replay, not by restating the former raw-depth blocker.

Added immutable frozen statistics, bounded archive copying (128 MiB), source
checksums and a fingerprint, and production hierarchy reconstruction after
filtering completed outcomes by each decision cutoff. Missing archive parts,
unknown dates and future outcomes are not silently accepted. Per-boundary trace
records query, counts and hierarchy. No production changes or mutations.

Actual source: reports/calibration/scalping-v2-probability-set2 is the shared
reports mount used by both production orchestrator and collector. Runtime source
scripts/engine_orchestrator_online_pipeline.py wires PostgresPaperOutcomeStatisticsSource.
53 closed PAPER records belong to an older runtime parameter set; they are
excluded by exact parameter-set filtering for Set #2. 636 compatible prospective
outcomes were loaded, 607 completed before 23:00 UTC on 2026-09-13.

The frozen all-10-symbol dataset and baseline plus 27 grid points were reused.
At reached decisions, 581–606 compatible completed outcomes were eligible.
150 repeated configuration/boundary cases reached the statistical gate; all
replayed SCALPING_EMPIRICAL_EXPECTANCY_REJECTED. No admitted trades, no PnL or YAML
findings. These counts are not independent opportunities or a full search-space
exhaustion proof. The formerly documented 23 missing-cost boundaries remain
specific to expanded stop-envelope combinations, not a universal dataset block.

Exact historical membership remains unverified: collector completed_at is stamped
before append/fsync, without a published_at/reader-visible sequence ledger or
archived manifest at each decision. The adapter therefore reports
STATISTICS_REPLAYED_NOT_CERTIFIED. This is narrower than saying historical
probability data does not exist. It does not prove reconstruction from another
archive impossible. No arbitrary replacement of absent history was made.
Required next evidence: an as-of archive/membership record establishing the outcomes
available to the required decision, or an explicitly separate modeled-availability
contract. The original final gate requires HISTORICAL_VERIFIED, so the modeled
completion-time calculation is not promoted to that status.

Remaining implementation also includes full upstream recomputation, chronological
portfolio/lifecycle simulator, optimizer, verified YAML exports, new GUI workflow
and final real profitable-trade acceptance. These are uncompleted work, not claimed
external failures. No PASS for blocks 02–07 or the full prompt is claimed.

Tests: 59 passed; compile PASS; fresh committed process replay produced identical
combination results and traces to the prior process. Committed freeze smoke also
passed. Deployment is direct Python checkout, not a production service restart.
Source commit = 82c71bc2aa80d8bea910bff2c1e61ddbfeebd7aa
Interpreter = C:/Program Files/Python311/python.exe
Dataset = artifacts/result_search_applicability_01/dataset
Statistics = artifacts/result_search_applicability_01/STATISTICS.json
Replay = artifacts/result_search_applicability_01/STATISTICS_ACCEPTANCE.json
Commands are documented in docs/research/scalping_v2_parameter_sweep.md.
Tracked compact evidence = TRADERS_HISTORICAL_STATISTICS_CONTINUATION_01_RESULTS.json.

Safety: trading YAML unchanged SHA256
70bba34921cdfb49709771068dd1ca53641dd4e9811ebd50046ef5aaf4989499;
no production restarts, orders, activation or LIVE enablement. Existing services
observed running. Primary ACK owner blocker and module percentages unchanged.

FILES_CHANGED = traders_ml/parameter_sweep/historical_statistics.py;
traders_ml/parameter_sweep/history_applicability.py;
tests/research/test_historical_statistics.py; docs/research/scalping_v2_parameter_sweep.md;
docs/audits/TRADERS_HISTORICAL_STATISTICS_CONTINUATION_01_FINAL.md;
docs/audits/TRADERS_HISTORICAL_STATISTICS_CONTINUATION_01_RESULTS.json; online_trader.md
Project-state evidence commit: git log -1 --format=%H -- this file.
Documentation commit: git log -1 --format=%H -- online_trader.md.
Final push/remote verification follows reconciliation and is in task handoff.
