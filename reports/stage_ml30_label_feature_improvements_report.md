# Stage ML30 - Label Feature Improvements

ML30 adds gap-aware dataset filtering, feature quality diagnostics, anti-collapse training controls, candidate acceptance thresholds, and an expanded label quality grid.

The gap-aware layer can exclude windows around detailed candle gaps before retraining. When only aggregate gap counts are available, the dataset remains unsafe for strict training decisions until detailed timestamps are collected.

The new feature quality diagnostic measures class separation, missingness, constant features, and low-variance features. This supports faster removal of weak inputs before the next label grid cycle.

The anti-collapse training plan documents safer training controls around class weights, sampling, confidence margins, and prediction distribution gates. These controls remain research-only and do not authorize live use.

Candidate acceptance thresholds are centralized and now drive clearer selector explanations for baseline edge, collapse, profit-aware, walk-forward, and gap quality gates.

The label quality grid now includes both the original ML27 family and new ML30 configs with stricter flat thresholds and longer horizons.

Safety remains unchanged: no traders-core, no live, no orders, no auto activation. ML31 should run the broader grid only after the ML30 controls and diagnostics are in place.
