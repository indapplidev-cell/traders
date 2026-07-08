# ML38.10.70 — POST_FIELD_CONTRACT_SOLUSDT_QUICK_QUALITY_RERUN_READINESS_NO_RUN

## Why this stage follows ML38.10.69

ML38.10.69 implemented and tested the future sidecar field contract without a real run. ML38.10.70 is the no-run readiness gate for a separately approved, single SOLUSDT quick-quality wrapper run that could generate sidecars under that contract.

ML38.10.69 full pytest evidence is available outside the repository: `1160 passed, 0 skipped, 0 warnings`, exit code 0, pytest time 94.26 seconds, wall time 97.5170548 seconds. Log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_69_static_probe_fix_20260707_235953.log`.

## Field contract and static probe evidence

The `ml38.10.69` field contract includes stable temperature-1 softmax raw probabilities from `direction_logits`, current temperature-scaled calibrated probabilities, `actual_label` from `source_row.direction_label`, calibrated legacy aliases `prob_down/prob_flat/prob_up`, explicit raw/calibrated/sidecar-selected prediction layers, and a deterministic `row_alignment_key`. Downstream policy is unavailable in the writer and is not conflated with sidecar argmax. Fail-closed validation occurs before artifact-directory creation.

The ML38.10.55 static probe fix explicitly allows target-only `actual_label` export while proving `actual_label` is not used for prediction. Prediction labels remain probability argmax; no label substitution was detected. The sidecar writer contract was not changed by that narrow probe fix.

## Wrapper readiness and future scope

`run_solusdt_quick_quality_once.py` exists, targets SOLUSDT quick-quality only, and requires both `--execute` and `--i-understand-this-runs-real-quick-quality`. The exact command allowed only after separate approval is:

`python run_solusdt_quick_quality_once.py --execute --i-understand-this-runs-real-quick-quality`

Explicit no-run statement: wrapper/quick-quality/training not executed. `run_fv3_cached_tuning.py` was not run. The future scope is one SOLUSDT quick-quality wrapper run only; BTC, ETH, multi-symbol, clean, fast-debug, sequence, cascade/outcome, and production-like recompute remain excluded.

The wrapper also enforces a clean worktree at execution. Separate approval does not bypass that check; reconciling it with the user's no-commit workflow is a user decision before actual execution.

## h08 risk and dirty worktree policy

h08 risk: candidate boundary is 6485 vs 6481 global expected denominator, delta +4; the h08 fix was not applied. This is kept separately scoped because prior behavior indicates it may fail one h08 candidate without blocking the 45 h12 sidecar sets. It therefore does not block this readiness decision.

Dirty worktree policy: dirty status is expected from the uncommitted ML38.10.69 implementation under the user's changed workflow. This prompt requires no commit/planning/snapshot. No unexpected runtime JSON, ZIP, report-output, or log artifacts were detected in git status. A future real run from uncommitted code has a reproducibility risk because its exact source state is not commit-addressable; additionally, the current wrapper will reject dirty status. Commit or another compatible workflow resolution before a real run remains `USER_DECISION`.

## Verification

`py_compile` passed for the ML38.10.70 diagnostic. ML38.10.70 diagnostic tests passed (7), ML38.10.70 report tests passed (2), and targeted regressions passed for ML38.10.69 (18), ML38.10.55 (13), ML38.10.68 (8), and ML38.10.67 (6). `TrainingService` imported successfully. Class-weight collect-only found 1 test. `git diff --check` passed with only existing line-ending warnings.

The single permitted ML38.10.70 full pytest run completed with `1169 passed, 0 skipped, 0 warnings`; exit code 0; pytest time 87.56 seconds; wall time 91.0184611 seconds. External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_70_20260708_070328.log`. No pytest log was written under `reports/`.

## Decision and next stage

Final readiness decision: `READY_FOR_SEPARATELY_APPROVED_SOLUSDT_QUICK_QUALITY_RERUN`.

Recommended next stage: `ML38.10.71 — separately approved SOLUSDT quick-quality rerun`, subject to explicit user approval and resolution of the wrapper clean-worktree precondition. The real run is not authorized by ML38.10.70.

Blockers retained: cascade/outcome blocked; production-like recompute/tradable edge blocked. No tradable edge is claimed.
