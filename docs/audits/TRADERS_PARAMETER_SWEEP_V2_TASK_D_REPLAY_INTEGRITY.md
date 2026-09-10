# Parameter Sweep v2 — Block D replay integrity

TASK_STATUS = PASS
DATASET_HASH = 7235d52b13af65583117464660d0f1eb2691e4fd5046e292a494d1252e298b55
FROZEN_CUTOFF = 2026-09-07T20:55:00+00:00
BASELINE_PARITY = PASS_WITH_EXPLICIT_DATA_AVAILABILITY_CLASSIFICATION
UNEXPLAINED_PARITY_MISMATCHES = 0
LOOKAHEAD_VIOLATIONS = 0_CHRONOLOGICAL_SPLITS_AND_CLOSED_BOUNDARIES
COST_PROVENANCE_COMPLETE = YES_FROZEN_ROW_LEVEL_SOURCE
DETERMINISM = PASS_DATASET_RESEARCH_BASELINE_SEED_CONFIG_IDS_AND_RANKING_SIGNATURE

Replay continues to reuse production stop/target, cost, EV, probability, risk,
selector and stale-position evaluators. A persisted trade lacking a causally
matchable opportunity in the frozen snapshot is now explicitly classified
`EXPLAINED_BY_DATA_AVAILABILITY`; it is not counted as an unexplained evaluator
mismatch. Recovery/operator mismatches remain separately explained. Holdout is
chronological and excluded from selection.

Resume checks dataset manifest/fingerprint, research/search-space fingerprint,
baseline hash, schema and engine compatibility separately. New production rows
cannot mutate an existing frozen run.

