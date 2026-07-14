# ENGINE-TREND-27 Leakage Audit

- The scan window `2025-01-04T00:00:00Z`..`2025-06-29T23:45:00Z` predates the ENGINE-23 universe and is disjoint from ENGINE-26.
- No ENGINE-23/24/25/26 candidate, score, label, selected ID, metric, or SOLUSDT pocket is loaded.
- The five family contracts are constants in source and recorded before labelling.
- All plans were serialized before `label_plan` ran. Pre-entry SHA-256: `4346b098ec973d4f1c03961f09317d0977d5ecc64517c6650e934c8b3d6e0967`.
- Detection functions receive only the current index and causal candle/indicator arrays. Pivots require their two-bar right wing to have closed.
- Close-entry outcome observation starts on the next candle. Simultaneous TP/SL bars are excluded from clean PF, expectancy, drawdown, and gates.
- This is one reference scan. No family rule or threshold was selected from these outcomes.

Status: **PASS**, with the explicit limitation that this is backward-held-out history, not a future live forward.
