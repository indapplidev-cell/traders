# Block 09 — durable causal opportunity dedupe

```text
TASK_STATUS = PASS
POLICY = ONE_EXECUTION_PER_CAUSAL_OPPORTUNITY
BOUNDARY_ALONE_RESETS = NO
STATE = ATOMIC_DURABLE_JSON_REGISTRY
DEFAULT_STATE_PATH = reports/runtime/scalping_opportunities.json
PERSISTED = causal_opportunity_id,causal_parent_id,reset_reason,reset_evidence,prior_execution_position_id,duplicate_block_reason
STRUCTURAL_RESET = NEW_IDENTITY_PLUS_NONEMPTY_REASON_AND_EVIDENCE
RESTART_SAFE = YES
LIVE = DISABLED
BINANCE_ORDER_API_CALLS = 0
```
