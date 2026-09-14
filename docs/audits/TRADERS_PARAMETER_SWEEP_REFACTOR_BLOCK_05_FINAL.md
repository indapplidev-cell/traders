# Result-search block 05: durable verified exports

FINAL_VERDICT = ENGINEERING_AND_INSTALLED_ACCEPTANCE_PASS_FINAL_TRANSPORT_GATE_PENDING

FindingVerifier persists the first profitable close as FOUND_CANDIDATE while the
current bounded trial completes. Only an entire valid period can be published:
engine/dataset/configuration/quality, causal admission, real close reason, fees,
net accounting and total period PnL are checked. A fresh isolated simulation from
the exported YAML must match the exact canonical result before publication.

The YAML includes the frozen baseline and all risk values through a dedicated
inactive named-set definition. The normal production loader parses it, and the
normal resolver accepts an explicit frozen source-authority context. That context
uses the existing research fingerprint; default production resolution and its
authority hash remain unchanged. Frozen risk is explicit in the export and is
not silently replaced by whichever risk policy is current at replay time.

Default target one stops scheduling after verification. Target K counts distinct
realized paths; inactive numerical changes cannot create duplicate findings.
Losing trades and a negative total period remain visible even when one trade wins.
Cancellation/crash before publication preserves candidates; resume processes
completed but unpublished trial records before scheduling. The successful index
is published only after YAML/result/proof files, each checksummed. Torn report
publication is rebuilt from the verified index on resume. Storage bounds prevent
oversized publication; no automatic strategy activation exists.

Outputs: SUCCESSFUL_CONFIGS.json, candidate_<hash>.yaml, WINNING_TRADES.jsonl,
REPLAY_PROOF.json, SEARCH_MANIFEST.json, REPORT.md, complete result_<hash>.json.
Independent validation and deployment readiness stay NOT_EVALUATED/NOT_ESTABLISHED.

Validation: 331 PASS across research, fill, native configuration and cycle-binding
tests; fresh installed verifier/optimizer suite 17 PASS. Stale test fixtures using
RR 0.6/target 60 were corrected to test declared current values or an explicit
isolated switch fixture. Invalid-YAML injection now edits the parsed override,
so it cannot silently miss a changed production value. Production YAML unchanged.

Positive export, period loss, target K, numerical deduplication, cancellation,
crash recovery, future admission, evidence corruption, replay mismatch and storage
tests use explicit synthetic engineering fixtures. They do not prove real profit.

Installed source = 9e6e13d62e471bb84c082171f4a04997d57d2913
Engine = result-search-engine/4-verified-export
Installed PID = 3812; interpreter = C:/Program Files/Python311/python.exe
Direct checkout = D:/disk_E/game_projects/traders/traders-ml
Real baseline canary: one complete 480-boundary simulation, zero trades/net 0,
FOUND false; full YAML roundtrip reproduces identical result and resolved hash
f0e0e112e312bc1c4d792c6efa89ed85b96e5b89b836ed5168443bfe99227431.
Local evidence = artifacts/result_search_block05_committed_acceptance
ROUNDTRIP_BASELINE_NOT_A_FINDING.yaml is a replay check, not a winning candidate.

Reproduce: python -m scripts.result_search_verifier_acceptance --dataset
artifacts/result_search_block02_committed_acceptance_v2/dataset --output <new-directory>.
Replay a published candidate in a fresh process: python -m
traders_ml.parameter_sweep.finding_verifier --directory <campaign> --candidate <hash>.

FILES_CHANGED = app/config/trade_parameters.py; traders_ml/parameter_sweep/frozen_funnel.py;
traders_ml/parameter_sweep/result_search.py; traders_ml/parameter_sweep/chronological_search.py;
traders_ml/parameter_sweep/generated_search.py; traders_ml/parameter_sweep/search_optimizer.py;
traders_ml/parameter_sweep/finding_verifier.py; tests/research/test_finding_verifier.py;
tests/research/test_search_optimizer.py; tests/test_trade_parameters_config.py;
tests/engine_orchestrator/test_parameter_set_cycle_binding.py;
scripts/result_search_verifier_acceptance.py;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_05_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_05_ACCEPTANCE.json;
docs/research/scalping_v2_parameter_sweep.md; online_trader.md.

Project-state evidence commit: git log -1 --format=%H -- this report.
Documentation commit: git log -1 --format=%H -- online_trader.md.
Fresh push verification follows reconciliation in the task handoff.
Next block: 06 common GUI/CLI service and real Tk acceptance.
