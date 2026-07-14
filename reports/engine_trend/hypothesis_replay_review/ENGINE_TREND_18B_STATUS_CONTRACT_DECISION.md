# ENGINE-TREND-18B — Hypothesis Status Contract Decision

## Decision: variant A

Keep `CONFLICTED` and add `CANCELLED` as a distinct lifecycle state in a dedicated contract change.

- `INVALIDATED`: subsequent market evidence disproved the hypothesis.
- `CONFLICTED`: material competing evidence is simultaneously active.
- `CANCELLED`: the system retired an otherwise viable hypothesis because a stronger scenario superseded it.

## Transition constraint

`CANCELLED` must not be emitted merely because a competing score is higher. It requires an explicit supersession rule, `cancelled_by_hypothesis_id`, and a cancellation reason code. Trap/range ties in this replay remain `CONFIRMED` competitors, not cancelled hypotheses.

The runtime enum is deliberately not changed in audit stage 18B: adding an unused enum value without transition metadata would claim a lifecycle the engine does not implement. This contract is the acceptance criterion for the implementation stage before or within ENGINE-TREND-19.
