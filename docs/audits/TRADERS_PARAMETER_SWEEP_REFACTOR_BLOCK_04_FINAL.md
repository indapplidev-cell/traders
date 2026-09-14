# Result-search block 04: generated combinations

FINAL_VERDICT = ENGINEERING_AND_INSTALLED_ACCEPTANCE_PASS_FINAL_TRANSPORT_GATE_PENDING

The registry covers nine actual consumers across signal/setup, regime,
confirmation/entry, geometry and economics admission. Every remaining frozen
parameter has its value, path, type, unit and exclusion reason. Risk/capital,
external costs and production lifecycle remain fixed. Domains combine baseline,
search-only empirical quantiles and declared discrete options. Exit-tail and
independent-evaluation rows are excluded. Runtime constraints include regime
window covering structure and ATR geometry cohorts 0.25/0.5/0.75/1.0.

Optuna 4.5.0 is pinned in pyproject.toml's research extra; installed on Python 3.11.
Official compatibility/API references checked before integration:
https://pypi.org/project/optuna/4.5.0/
https://optuna.readthedocs.io/en/v4.5.0/reference/samplers/generated/optuna.samplers.TPESampler.html
https://optuna.readthedocs.io/en/v4.5.0/faq.html

One sequential worker uses local SQLite, immutable manifests and checksummed
trial records. Baseline runs first, then joint low/high starts, then TPE. Each
trial has a deterministic sampler seed (campaign seed + trial number) modulo
2**32, so SQLite resume does not depend on an unsaved Python RNG object. Small
finite domains use exhaustive enumeration. Configuration duplicates reuse an
integrity-checked result; behavior fingerprints are counted separately.

Objective: invalid/incomplete replay = -2; otherwise
2 * any-positive-closed-net-trade + atan(period-net-PnL) / pi.
Tie-break: objective descending, configuration fingerprint ascending. Gate
counts are diagnostic only. No pruning discards an initially inactive interval.
Interrupted simulations retain a pending trial for resume; crashes after atomic
result write recover without a second simulation. Waiting trials survive restart.

Tests: 307 PASS across affected research/history/simulation and PAPER fill suites;
48 PASS after final consumer constraints; frozen-registry metadata test 1 PASS.
Compile and staged diff check PASS. Tests include exhaustive reference coverage,
two-parameter joint-only success, deterministic TPE resume, invalid proposal
exclusion, pending/atomic-write crash recovery, every active runtime consumer,
search-only domain generation and exclusion of future boundary observations.

Implementation commits:
0a798f2da999b67f6fa44f4a797929e5ef69674c
591bc7fdfa5965ad0271d9642528b574b77deb33

Installed acceptance uses five generated trials on all ten symbols, 480 decision
boundaries per unique configuration, followed by resume with unchanged ledger
hashes. Detailed local evidence: artifacts/result_search_block04_committed_acceptance_v2.
Command: python -m scripts.result_search_optimizer_acceptance --dataset
artifacts/result_search_block02_committed_acceptance_v2/dataset --output <new-directory>.

This optimizer does not publish FOUND. Candidate verification/export is block 05.
No profitable historical trade has been established. Missing cost evidence blocks
only combinations reaching incompatible inputs; the dataset is not globally blocked.
No production services restarted, no activation/orders/business writes performed.

FILES_CHANGED = pyproject.toml; traders_ml/parameter_sweep/result_search.py;
traders_ml/parameter_sweep/chronological_search.py;
traders_ml/parameter_sweep/search_parameters.py;
traders_ml/parameter_sweep/search_optimizer.py;
traders_ml/parameter_sweep/generated_search.py;
tests/research/test_search_optimizer.py; tests/research/test_search_parameters.py;
tests/research/test_frozen_funnel.py; scripts/result_search_optimizer_acceptance.py;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_04_FINAL.md;
docs/audits/TRADERS_PARAMETER_SWEEP_REFACTOR_BLOCK_04_ACCEPTANCE.json;
docs/research/scalping_v2_parameter_sweep.md; online_trader.md.

Project-state evidence commit: git log -1 --format=%H -- this report.
Documentation commit: git log -1 --format=%H -- online_trader.md.
Fresh final remote verification follows reconciliation, recorded in task handoff.
Next block: 05 durable FindingVerifier and exported configuration replay.

Fresh installed PID 19872, source 591bc7fdfa5965ad0271d9642528b574b77deb33: five trials, four unique configurations and behaviors; three complete no-trade simulations and one combination blocked on 60 reached cost inputs. Resume preserved every trial checksum. Net PnL 0; FOUND false. Read-only SQL corroboration and invariant hashes are in the acceptance JSON.
