# Stage ML38.10.36 — Threshold Sensitivity / Flat-Bias Root-Cause Audit

## Goal

Explain why metric overlap is missing, why min_count=1 is harmful, and why FLAT is underpredicted.

## Constraints

- No clean_traders_ml.py
- No fast-debug
- No quick-quality
- No full run
- No live trading
- No auto-activation
- No gate softening
- No lv37 trading filter

## Implemented

- threshold sensitivity board
- aggregate threshold sensitivity board
- flat-bias root-cause audit
- walk_forward_summary.total_r_by_symbol mapping fix
- reporter propagation

## Validation

- py_compile: passed
- targeted pytest: 9 passed
- related pytest: 15 passed
- full pytest: 824 passed

## Expected runtime follow-up

After user runs runtime manually:

- fast-debug expected candidate_count remains 44
- quick-quality expected candidate_count remains 46
- accepted_candidate_count expected 0 unless model quality genuinely changes
