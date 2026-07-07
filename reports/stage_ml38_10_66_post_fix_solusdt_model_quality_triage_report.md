# ML38.10.66 — Post-fix SOLUSDT model quality triage

## Why this stage follows ML38.10.65

ML38.10.65 established that the post-fix real SOLUSDT quick-quality wrapper and child completed with exit code 0, the earlier TypeError did not repeat, and 45 complete sidecar sets passed byte, LF, schema, summary, runtime, completion, and archive checks. ML38.10.66 therefore returns to model quality and explains the 45 rejected candidates and 1 failed candidate without another run.

## Latest run evidence

- Output: `reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260707_151645`
- ZIP: the matching `.zip` archive
- External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\solusdt_quick_quality_20260707_181639.log`
- Completion marker: matching `.completion.json`; child exit code 0 and elapsed time 13,430.093 seconds
- Read-only inventory: 435 files, including 244 JSON and 141 Markdown files
- Primary status source: `label_grid_experiment_summary.json`

## Candidate status summary

There were 46 total candidates: 0 passed/accepted, **45 rejected**, **1 failed**, and 0 unknown. Status confidence is HIGH because the label-grid summary, per-symbol summary, candidate results, pipeline reports, and aggregate analysis agree.

## Failed candidate analysis

The failed candidate was `lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax`. It failed in `train_model` with: `full-dataset prediction sidecar is not ready: row_count 6485 does not equal expected_row_count 6481`.

No traceback was stored, the old TypeError did not repeat, and this was not a quality evaluation rejection. It was a sidecar denominator/export contract failure caused by applying the h12 fixed expectation to an h08 dataset. Before retrying h08, ML38.10.67 should add a targeted contract test and make expected rows derive from the candidate dataset boundary. Existing real artifacts must not be rewritten.

## Rejected candidate analysis

All 45 completed candidates were `QUALITY_REJECTED`. All 45 failed `baseline_edge_gate`, so they share the same primary rejection reason. Other explicit gate counts were:

| Reason | Candidates |
|---|---:|
| `baseline_edge_gate` | 45 |
| `walk_forward_gate` | 38 |
| `research_only_fold_1_exit_time_slice_repair_probe_gate` | 25 |
| `profit_aware_gate` | 16 |
| `research_only_validation_total_r_repair_gate` | 2 |

The binding evidence is model separation: model accuracy was 0.188078 against a FLAT-majority baseline of 0.923947, an accuracy edge of -0.735868. Positive profit proxies do not override this: 31 candidates had positive full-sample PF and total R, but only 8 had positive walk-forward PF and total R.

## Grouped rejection reasons

- Gate policy — HIGH: baseline edge failed 45/45; no gate relaxation is supported.
- Walk-forward stability — HIGH: 38 failures; the audited worst fold had validation total R -37.2088 with stop/mitigation losses dominant.
- Directional coverage — HIGH: actual test directional support was only 74/973 rows, while predictions were directional on 864/973 rows.
- Calibration — HIGH: actual labels were DOWN 31, FLAT 899, UP 43, but predictions were DOWN 472, FLAT 109, UP 392. Average probabilities were 0.37344/0.26507/0.36149 for DOWN/FLAT/UP.
- Class balance / label distribution — HIGH: FLAT was 92.39% of test labels; all 45 completed candidates exposed the same test distribution.
- Profit/risk proxy — HIGH: 16 profit-aware failures; aggregate positives were not fold-stable.
- Data quality / config consistency — not a rejection driver: the 45 completed sidecars were valid with zero effective training gaps and no label substitution.
- Other — MEDIUM: 27 candidates depended on explicitly research-only repair probes. All 45 also recorded the internally inconsistent pair `collapse_detected=true` and `collapse_type=NONE`; this is context, not an independent acceptance reason.

## Quality blocker ranking

1. Negative edge versus the FLAT-majority baseline — affects 45.
2. Probability calibration and label/prediction distribution mismatch — affects 45.
3. Walk-forward instability — affects 38.
4. Research-only repair dependence — affects 27.
5. Profit/risk weakness — affects 16.
6. h08 sidecar denominator mismatch — affects the one failed candidate.

## Sidecar context

All 45 produced sidecar sets were valid. The latest SHA-256 was `5ef2a0492f33686e5885fe9d2128bf223df8d4b7c0f0939fd3486f0d8100f3c4`, size 6,837,243 bytes. Exact-byte, LF-only, schema, summary-contract, runtime-truth, and archive validations passed. Label substitution was not detected and sidecar bytes were not mutated during this stage.

## Model quality context

The completed candidates used `fv4_book_setup_context`, SOLUSDT 15m, primarily horizon 12. Each completed dataset had 6,481 rows split train 4,536, validation 972, and test 973. The model family was candle MLP with the two-stage trade objective. The best-ranked rejected candidate had full-sample PF 1.407 and walk-forward PF 1.072, but remained blocked by baseline edge and a research-only repair gate.

## Selected next training/quality action

For **ML38.10.67**, select `CALIBRATION_TUNING`: implement a read-only replay over the 45 existing sidecars, compare raw versus calibrated probabilities, and test bounded decision-policy settings for FLAT recovery. Rank replay results by baseline edge, every-fold stability, and unchanged profit/risk gates. This is the selected next training/quality action because it tests the common 45/45 failure hypothesis in minutes before another multi-hour real run.

Expected ML38.10.67 files are a new sidecar calibration replay diagnostic, its targeted tests and report, plus an h08 sidecar expected-row contract test. `app/labels/label_quality_grid.py` should only be changed in a later stage if replay evidence selects a bounded calibration zone. The next command is targeted pytest followed by the read-only replay against the existing sidecars; no `run_fv3_cached_tuning.py` invocation is needed. ML38.10.67 requires no real training run.

## Execution guardrails

This stage performed **no rerun** and no wrapper execution. It performed no training/runtime execution, DB writes, `ml_labels` writes, `ml_predictions` writes, label/builder/gate/model/analyzer changes, artifact normalization, summary/ZIP recreation, archive recovery, or artifact deletion. Existing real artifacts were read only; no new sidecars or ZIP were created.

Explicitly: **cascade/outcome blocked**; production-like recompute not claimed; this is **not tradable edge**, and tradable edge is not claimed.

## Tests run

The allowed py_compile, two ML38.10.66 targeted test files, three regression-targeted test files, TrainingService import, class-weights collect-only, and `git diff --check` passed. The subsequently authorized full regression suite also passed:

- Result: **1122 passed, 0 skipped, 0 warnings**
- Exit code: `0`
- Pytest time: `100.70s`
- Wall time: `105.596s`
- External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_66_20260707_222359.log`

The final candidate summary remains 46 total, 0 accepted, 45 rejected, and 1 failed. The failed h08 candidate stopped at `train_model` because its sidecar had 6,485 rows versus the fixed expectation of 6,481; the TypeError did not repeat and quality evaluation was not reached. The main blocker remains actual FLAT 899/973 versus predicted FLAT 109/973, with accuracy edge -0.735868.

## Final decision

`POST_FIX_SOLUSDT_QUALITY_TRIAGE_COMPLETED_NEXT_ACTION_SELECTED`

Next allowed stage: **ML38.10.67 — CALIBRATION_TUNING**. It will perform read-only raw/calibrated probability replay over the 45 valid sidecars and add the h08 denominator contract test. No new training run is needed yet.

The decision remains fail-closed: **cascade/outcome blocked; production-like recompute blocked; tradable edge claim blocked**.
