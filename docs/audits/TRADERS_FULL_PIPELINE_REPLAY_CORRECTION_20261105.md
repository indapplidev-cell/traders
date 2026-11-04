# Full-pipeline replay correction — 2026-11-05

## Verified baseline

- Frozen dataset hash: `f820eb6809d74726494740010432cf49d3dd69896f5af4a1dc780cad5c80db89`.
- Baseline v2: 20 symbol `DONE.json` markers; 592,196 decision traces; 12,552 pre-holdout opportunity rows. The locked holdout file is present but has not been evaluated.
- 981 closed simulated trades; gross PnL 2.736046, net PnL -419.144490, 421.880536 reported fees and 71.151372 reported slippage. These last two fields do not reconcile to net because the v2 cost decomposition is wrong.
- SHA-256: `BASELINE.json` `00d51132d6479810227cf38d9bc63a048766bfe968555ba21f1acc2d18922d8b`; `DECISION_TRACES.jsonl` `b1bbbe77359781b7a40fd6e400ab307d0c4864ad43b99d229287c62743d6ab29`; `REPLAY_ROWS.jsonl` `5f26f88b07fd2bf0af3385b4e8497193418b88dc2a017673d44cd78482a00db3`; locked holdout `3c2d385531f315617c95176412c8b972e41ce1b0aaf81c07803f3585ca21dcca`.

## Defects and correction in this commit

1. `train_ragged` previously scored sensitivity and TPE trials on the final validation interval. It now partitions all shared calendar validation intervals out of training, clips 1m execution paths at role boundaries, searches only training rows, and uses final validation to rank a training-derived shortlist.
2. Baseline v2 serializes only observations for which the current production configuration already supplied valid entry, stop and target. Its 12,552 replay rows cannot recalibrate analysis and setup decisions on the remaining boundaries. The training command now fails closed with `FULL_PIPELINE_FEATURE_CACHE_REQUIRED` until a v3 cache contains every causal stage's primitive evidence and supports per-candidate recomputation.
3. The v2 trade exporter labels all costs as fees and zeroes spread, slippage and reserve. The v2 result therefore cannot pass the requested accounting or verifier gates. It must be reconstructed with explicit cost components before candidate evaluation.

## Next implementation stage

Build a compact v3 causal feature cache for each closed boundary, capturing native module outputs, setup features, scoring inputs, causally available geometry inputs and component cost evidence. Recompute stages and price paths for every candidate in one global portfolio clock. Add stage activity and parity checks, then rerun baseline and training. Keep the internal holdout locked until immutable finalist freeze; never promote an unverified candidate.

No training candidate or recommended weights were produced in this stage. Production parameters and LIVE were not changed.
