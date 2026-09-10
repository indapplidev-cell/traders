# Task B — runtime resolution and provenance proof

```text
STATUS = PARTIAL_ACTIVE_5M_PROVENANCE_PASS_GLOBAL_FALLBACK_ZERO_NOT_CERTIFIED
LATEST_CYCLE = 1789014900000
LATEST_SYMBOLS = 10
PROFILE = trade-5m-v2
PARAMETER_SET = scalping-v2-set-2
RESOLVED_CONFIG_HASH = 536fd1adafe68f0c3f6095303fb3954b38196285ad66c656073516fbeed87839
SERVER_REVISION = 8ab9627175726526f4f92f2798c59d7c7ad3b1f4
COLLECTOR_REVISION = 60ba8ad62290f81cdb44510a5c519ccfb184d238
SEMANTIC_CHANGE_COUNT = 0
```

The latest complete 5m boundary persists profile, Set #2 identity, activation
revision, full flattened parameter/runtime/operational snapshots and the same
config hash on all ten symbols. Runtime provenance covers signal/setup,
impulse, regime, geometry, stop/target, costs, probability, RR/EV, risk,
portfolio, lifecycle, execution and collector policy. Typed loaders fail closed
for required YAML keys; the focused resolver/YAML tests passed.

The re-audit fixed one research/finalizer defect: calibration replay constructed
`ShadowGeometryConfig` with 0.25/80/45 and RR 1.5. It now resolves the active
geometry/economics and research cohorts through typed YAML authorities. This
does not alter the production evaluator or effective YAML and leaves the active
soak hash unchanged.

PASS is withheld because repository-wide counts for Python, legacy-profile,
generic-config and research fallback paths cannot be certified as zero while
Task A has 317 untraced candidates. Evidence is in `runtime_provenance.json` and
`latest_runtime_provenance.json`.
