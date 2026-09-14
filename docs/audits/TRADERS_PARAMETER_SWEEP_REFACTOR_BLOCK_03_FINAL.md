# Result-driven parameter sweep — block 03

FINAL_VERDICT = IMPLEMENTATION_AND_INSTALLED_ACCEPTANCE_PASS
BLOCK_PASS = final documentation/push gate resolved in the task handoff

The block 02 dependency is resolved. The new offline adapter invokes the actual
PipelineRunner from closed market history, with an explicit resolved configuration,
local runner stores, causal snapshots, recorded costs and validated historical
statistics. It recalculates analysis/setup/strategy/risk/geometry/economics.
The internal CLI runs a chronological multi-symbol trial; no production service,
order mutation or live API is called.

| Requirement | Evidence |
| --- | --- |
| Explicit configuration and independent trials | Typed frozen trading values; own research fingerprint; frozen runtime consumer values checked; no global configuration mutation |
| Parameter consumers | Nine supported keys cover signal/setup, regime, confirmation, geometry and economics; explicit runtime tests; real score threshold changes 255 decisions |
| Authoritative baseline parity | 480/480 PAPER statuses and rejection reasons match recorded baseline across all 10 symbols |
| GLOBAL book and selector | Chronological common capital, shared quantity sizing/instrument constraints, shared portfolio gate, canonical eligible candidate ranking |
| Lifecycle | Shared stop-first exit evaluator; next eligible closed 1m open fill semantics; expiry checked before costs; SHADOW timeout does not close positions; gaps and incomplete tails never become successful exits |
| Accounting | Shared Decimal adverse fill/fee/PnL calculations; fees once; LONG/SHORT full production fill price/fee parity; expectancy money and R separate |
| Causality and trace | Search boundaries only; per-decision candle cutoff; decision/config/dataset/source candle trace; exits processed as their candles close |
| State isolation | ResearchOpportunityRegistry uses original claim/reset/execution methods with memory-only persistence; file access prohibited by test |
| Required inputs | Diagnostic cost query does not become an admission blocker; missing required admission/quantity/exit-time inputs remain explicit |
| Evidence quality | Explicit execution assumptions remain ASSUMPTION_BASED; input quality is never promoted |

Actual installed trials on dataset a890247e7f011691c1a50344a72edd1354907ff72f7f7748237d6fdc40989a72:
- Baseline: 480 decisions, 480 matching historical decisions, no data blockers,
  zero trades, net PnL 0, ending balance 100.
- signal.strategy_minimum_score=100: 480 NO_PLAN decisions, 255 changed decisions;
  no data blockers, zero trades.
- geometry.stop_max_bps=60: 457 unchanged decisions; 23 newly reached boundaries
  require missing cost snapshots. These are BLOCKED_DATA, not fabricated losses.

The full profitable LONG/SHORT/loss/cost/selector lifecycle cases are synthetic
engineering tests only. No profitable historical trade or FOUND is claimed.
The actual baseline is a valid no-trade simulation. The simulation API is not
an optimizer and does not publish FOUND; blocks 04/05 add those responsibilities.

Tests: 300 passed (research contracts/history/statistics/funnel/execution/selector
and full PAPER fill simulator suite). After the engine version update, 34 affected
contract and chronological tests passed. Compile PASS; staged diff check PASS.
Fresh baseline repeat reproduced identical events, decisions and accounting.

Installed computation source = 5c5e02123a553fdcb6a9f70172dfaa5fb4e9dcab (PID 14180)
Three-trial source = 32f69eae73e11d73e8d1a0a4918b2268cc82da28 (PID 12460)
Final engine version/diagnostics source = dc42c237dcbef3da97bb900a0def0e7af318f753 (PID 14824)
Engine version = result-search-engine/3-chronological
Method = direct checkout D:/disk_E/game_projects/traders/traders-ml
Interpreter = C:/Program Files/Python311/python.exe
Evidence = TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_03_ACCEPTANCE.json
Local detailed trials = artifacts/result_search_block03_committed_acceptance_v2

Run one trial with an existing JSON overrides file and a new output path:
`python -m traders_ml.parameter_sweep.chronological_search --dataset artifacts/result_search_block02_committed_acceptance_v2/dataset --overrides <overrides.json> --capital 100 --output <new-result.json>`
Reproduce installed real acceptance:
`python -m scripts.result_search_simulator_acceptance --dataset artifacts/result_search_block02_committed_acceptance_v2/dataset --output <new-directory>`
Optional --execution-assumptions accepts six explicit nonnegative bps components:
spread_bps, depth_impact_bps, entry_slippage_bps, exit_slippage_bps, entry_fee_bps,
exit_fee_bps. Such a run cannot satisfy historical-verified final acceptance.

Remaining limits: historical snapshots cannot establish arbitrary execution
quantity and future exit-time costs. A reached unsupported execution path is
blocked. Multi-epoch datasets require an explicit baseline; unsupported parameter
consumers are rejected. Lifecycle/risk/cost settings stay frozen in the searchable
registry at this stage. The source production composite hash includes unrelated
runtime/research/system authorities; a distinct canonical research fingerprint
retains that source hash and the full trading values instead of claiming equality.

Safety: production YAML SHA256 remains
70bba34921cdfb49709771068dd1ca53641dd4e9811ebd50046ef5aaf4989499.
Production services were not restarted; no live/orders/business writes. The local
opportunity file retains its 2026-09-06 write timestamp and recorded hash.

FILES_CHANGED = traders_ml/parameter_sweep/frozen_funnel.py;
traders_ml/parameter_sweep/historical_execution.py;
traders_ml/parameter_sweep/chronological_search.py;
traders_ml/parameter_sweep/opportunity_registry.py;
traders_ml/parameter_sweep/history_applicability.py;
traders_ml/parameter_sweep/result_search.py;
tests/research/test_frozen_funnel.py; tests/research/test_historical_execution.py;
tests/research/test_chronological_search.py; tests/research/test_research_opportunity_registry.py;
scripts/result_search_simulator_acceptance.py;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_03_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_03_ACCEPTANCE.json;
docs/research/scalping_v2_parameter_sweep.md; online_trader.md.

Project-state commit: git log -1 --format=%H -- this report.
Documentation commit: git log -1 --format=%H -- online_trader.md.
Final transport verification follows documentation reconciliation and is recorded
in the task handoff. Next block: 04 parameter generation and optimizer.
