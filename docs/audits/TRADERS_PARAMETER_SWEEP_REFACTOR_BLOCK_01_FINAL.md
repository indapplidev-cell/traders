# Result-driven parameter sweep — block 01

FINAL_VERDICT = ENGINEERING_AND_DEPLOYED_ACCEPTANCE_PASS_PENDING_TRANSPORT_GATE

Implemented typed SearchRequest, one-net-profitable-closed-trade criterion,
separate execution/outcome/evidence/independent-validation fields, shared headless
ResultSearchService and CLI/controller adapters behind explicit internal mode.
Versioned resume identity checks request, data, baseline, registry and engine.
FOUND requires VERIFYING state and durable, reread qualifying proof and matching
configuration. This is a foundation contract, not an implemented historical
simulator or independent FindingVerifier. Legacy workflows remain explicitly
legacy. No search success or YAML configuration is claimed.

Tests: test_result_search_contract.py 29 passed (including fresh committed run);
CLI/GUI v2, GUI pipeline and dynamic cold GUI suites 35 passed; compile and
whitespace validation passed. Tests use synthetic proofs only for contract tests.
They are not historical acceptance or trading evidence.

Deployment source = 026504126842b873749990aac23aa6ba025da706
Method = direct checkout, D:/disk_E/game_projects/traders/traders-ml
Interpreter = C:/Program Files/Python311/python.exe
Fresh diagnostics PID = 16752; module_dirty=false
Module SHA256 = 1367beee5ff81f8624044a94dfd5633a4bfeb34afbf42194a6e063afc7f41112
Fresh separate CLI processes prepared and resumed the same request successfully.
Local smoke evidence = artifacts/result_search_refactor/block01/smoke.json
The smoke uses an explicitly labelled sentinel dataset, and executes no search.

Production safety: no production code/config mutations, DB writes, restarts or
order calls. Read-only DB connection confirmed transaction_read_only=on.
Trading YAML SHA256 = 70bba34921cdfb49709771068dd1ca53641dd4e9811ebd50046ef5aaf4989499
Existing containers observed running; readonly/operator/Postgres healthy.
No fresh WAL/PITR, LIVE readiness or soak acceptance claimed.
User-deleted artifacts preserved and excluded from commits.

FILES_CHANGED = traders_ml/parameter_sweep/result_search.py;
traders_ml/parameter_sweep/cli.py; traders_ml/parameter_sweep/controller.py;
tests/research/test_result_search_contract.py;
docs/research/scalping_v2_parameter_sweep.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_01_FINAL.md; online_trader.md

Project-state audit commit is resolved by git log -1 --format=%H -- this file.
Documentation commit is resolved by git log -1 --format=%H -- online_trader.md.
Transport: remote read and push dry-run passed; actual push and fresh remote
verification are the final block gate, recorded in task handoff after commit.
Next block: 02 only after successful push/remote verification.
