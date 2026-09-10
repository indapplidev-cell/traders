# Task A — independent YAML authority re-audit

```text
STATUS = FAIL_ARCHITECTURE_CERTIFICATION_WITH_COMPLETE_INVENTORY
NEW_SCAN_FILES = 596
NEW_SCAN_SUSPICIOUS_VALUES = 5878
NEW_UNEXPECTED_POLICY_VALUES = 317
PREVIOUSLY_MISCLASSIFIED_VALUES = 317
UNKNOWN_REQUIRES_TRACE = 317
HARDCODED_POLICY_VALUES_REMAINING = NOT_PROVEN_ZERO
CROSS_YAML_DUPLICATE_AUTHORITIES = NOT_PROVEN_ZERO
REGISTRY_KEYS = 259
```

The independent AST inventory scans Python under `app/`, `traders_ml/`,
`scripts/`, `tests/`, Alembic and the Desktop source/tests/scripts. Vendor,
virtualenv, cache/build and generated evidence directories are excluded because
they are not project-owned executable source. The CSV contains every detected
candidate and exactly one classification.

The previous 447-file/4337-literal result was not sufficient evidence: it used
a guarded-file subset and reported zero unknowns. The broader scan found 317
policy-shaped assignments/defaults/fallbacks without an expression-local YAML
trace (server 274, Desktop 27, scripts 12, `traders_ml` 4). They include analysis
thresholds, sync timing/batches, PAPER budgets/readiness limits, research
horizons and Desktop transport limits. Some may become documented structural or
deployment constants after manual tracing; none may be silently waived.

Evidence: `artifacts/final_yaml_authority_reverification_01/HARDCODE_REAUDIT.csv`,
`summary.json`. PASS is withheld until all 317 rows have explicit ownership and
the semantic cross-YAML duplicate check proves zero.
