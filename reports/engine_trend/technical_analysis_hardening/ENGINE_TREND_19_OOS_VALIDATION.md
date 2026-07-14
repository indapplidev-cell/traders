# ENGINE-TREND-19 — Balanced Out-of-Sample Validation

Status: **BLOCKED_MANUAL_LABELS**.

- raw rows: 60
- unique periods: 45
- balanced UP/DOWN/FLAT rows: 27
- chronological train/test: 18/9
- independently manual-labelled test rows: 0/9
- proxy test metrics: `{"exact_match_count": 4, "exact_match_rate": 0.4444444444444444, "unknown_count": 3, "unknown_rate": 0.3333333333333333, "opposite_direction_count": 0, "decided_count": 6, "decided_accuracy": 0.6666666666666666, "confusion": {"DOWN->FLAT": 1, "DOWN->UNKNOWN": 1, "DOWN->DOWN": 1, "FLAT->UNKNOWN": 1, "FLAT->UP": 1, "FLAT->FLAT": 1, "UP->UP": 2, "UP->UNKNOWN": 1}, "class_counts": {"DOWN": 3, "FLAT": 3, "UP": 3}}`

The proxy split is suitable for regression diagnostics only. Production acceptance remains blocked until every OOS test period is labelled manually without engine predictions being visible to the reviewer.
