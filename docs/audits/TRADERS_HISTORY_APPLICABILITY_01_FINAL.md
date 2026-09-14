# Historical applicability correction 01

FINAL_VERDICT = PASS_REQUESTED_BLOCKER_CORRECTION_AND_BOUNDED_ASSESSMENT
ORIGINAL_SEVEN_BLOCK_PROMPT = NOT_COMPLETED

The previous universal raw-depth/cost-coverage blocker was overly broad and is
superseded. History schema 2 reports conditional input requirements separately
from candle gaps and missing tails. Frozen risk decisions and parameter values
are retained so that unchanged upstream inputs are explicit. No live values are
substituted. The authoritative ScalpingPaperRunner is used with an offline cost
source, frozen runtime parameters and isolated boundary-local state.

Real dataset: all 10 universe symbols, 2026-09-13 19:00–23:00 UTC; 480 boundaries,
11,850 candles; same interval as the earlier blocked audit. Fresh read-only
extraction retained additional causal inputs. No boundary gaps/duplicates.
Baseline parity: 480/480 tested rejections and numeric diagnostic fields match.
319 boundaries reject before costs; 161 reuse compatible derived snapshots.
Raw depth is unnecessary for these unchanged entry/reference-quantity inputs.
30 of the 161 reproduce the engine's invalid-level rejection for negative depth
impact values; they are not silently clamped or promoted into admissible trades.

Bounded combinations: baseline plus 27 Cartesian combinations:
stop_max_bps = 30 / 48.496589 / 60;
min_net_edge_bps = 1 / 20 / 73.004386;
minimum_planned_rr = 0.6 / 1.2 / 1.953403.
All other parameters frozen. Values declared before assessment; no trade outcomes
used to generate them. One grid point equals baseline: 28 evaluations, 27 unique
resolved combinations, not 28 independent findings.

Results: 9 evaluations (8 unique combinations) resolve every boundary as a
verified rejection. 10 evaluations have compatible cost evidence but reach the
probability stage on 1–26 boundaries, requiring historical probability hierarchy.
9 evaluations with stop_max_bps=60 expose 23 boundaries without required cost
snapshots. They remain specifically blocked; missing costs elsewhere do not poison
the whole dataset. Full trade simulation, portfolio, exits, PnL and FOUND are not
claimed. Upstream signal/regime/confirmation changes require actual recomputation.
The 3 supported dimensions are scope of this assessment, not the final optimizer.

Example (stop, edge, RR):
30, 1, 1.953403: 480 verified rejections, no new cost inputs required.
48.496589, 1, 0.6: 454 verified rejections, 26 probability prerequisites.
60, 73.004386, 1.953403: 457 verified rejections, 23 missing required costs.

Tests: 56 passed (applicability, history, contract, CLI/GUI v2); compile PASS.
Regression cases cover early rejection without costs, incompatible entry/quantity,
symbol, stale/future timestamps, policy changes, invalid combinations, missing
probability, baseline tampering, trial independence and candle coverage blockers.
Installed direct-checkout fresh CLI process completed all 28 evaluations. Counts
and reasons matched the prior process. No Tk or GUI changes were required.

Deployment source = 68a44a09d80a780e2493d2e0e450312e374d0c74
Interpreter = C:/Program Files/Python311/python.exe
Checkout = D:/disk_E/game_projects/traders/traders-ml
Results = docs/audits/TRADERS_HISTORY_APPLICABILITY_01_RESULTS.json
Local frozen dataset = artifacts/result_search_applicability_01/dataset
Local full trace = artifacts/result_search_applicability_01/COMMITTED_ASSESSMENT.json
Reproduction command is in docs/research/scalping_v2_parameter_sweep.md.
Large source histories remain untracked. Three reduced causal rows are test fixtures.

Production safety: no production code, settings, orders or DB mutations; no
production restarts; trading YAML SHA256 remains
70bba34921cdfb49709771068dd1ca53641dd4e9811ebd50046ef5aaf4989499.
Primary ACK owner blocker and module percentages unchanged. No soak/LIVE acceptance.

FILES_CHANGED = traders_ml/parameter_sweep/search_history.py;
traders_ml/parameter_sweep/history_applicability.py;
tests/research/test_history_applicability.py;
tests/research/fixtures/result_search_applicability.json;
docs/research/scalping_v2_parameter_sweep.md;
docs/audits/TRADERS_HISTORY_APPLICABILITY_01_RESULTS.json;
docs/audits/TRADERS_HISTORY_APPLICABILITY_01_FINAL.md; online_trader.md

Project-state evidence SHA: git log -1 --format=%H -- this file.
Documentation SHA: git log -1 --format=%H -- online_trader.md.
Final transport verification is recorded after reconciliation in task handoff.
Next: provide/reconstruct as-of probability hierarchy for reached candidates and
finish the historical simulator contract. Do not reinstate a universal book gate.
