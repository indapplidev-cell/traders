# PAPER command ingestion and entry-order creation

`app.engine_paper.command_ingestion_service.PaperCommandIngestionService` is a
callable application service. It consumes one explicit, finalized PAPER
approval chain and creates one immutable command plus one ENTRY order. It does
not poll, fetch market data, simulate a fill, create a position, invoke order
execution, expose an API, or enable PAPER/LIVE.

## Integrated authority inventory

| AREA | FILE | SYMBOL | CURRENT_AUTHORITY | REUSED | ADAPTED | NEW | RATIONALE |
|---|---|---|---|---|---|---|---|
| Final strategy | `app/engine_paper/paper_approvals.py` | `PaperStrategyApproval`, `finalize_paper_strategy_approval` | Final PAPER strategy authority | yes | no | no | Research strategy remains causal only |
| Controlled quantity | `app/engine_paper/paper_approvals.py` | `PaperQuantityApproval`, `issue_paper_quantity_approval` | Sole approved quantity | yes | no | no | Bare `Decimal` is not accepted |
| Final risk | `app/engine_paper/paper_approvals.py` | `PaperRiskApproval`, `finalize_paper_risk_approval` | Complete final PAPER risk authority | yes | no | no | All four final flags are required |
| Compatibility | `app/engine_paper/paper_approvals.py` | `map_final_approvals_to_command_compatibility` | Authoritative command mapping | yes | no | no | Prevents caller field override |
| Command/order | `app/engine_execution/paper_models.py` | `PaperExecutionCommand`, `PaperOrder` | Immutable PAPER aggregates | yes | no | no | Existing Decimal-only contracts |
| State machine | `app/engine_execution/paper_state_machine.py` | `create_paper_order`, `transition_order` | CREATED to VALIDATED to OPEN | yes | no | no | No direct OPEN persistence |
| Events | `app/engine_safety/paper_domain.py` | `PAPER_ORDER_VALIDATED`, `PAPER_ORDER_OPENED` | Canonical transition vocabulary | yes | no | no | Reuses remediation vocabulary |
| Journal | `app/engine_journal/paper_events.py` | `PaperDomainEvent` | Immutable bounded audit record | yes | no | no | One projection per persisted event |
| Policy | `app/engine_paper/fill_policy.py`, `app/db/paper_models.py` | `PaperFillSimulationPolicy`, `PaperSimulationPolicyRecord` | Immutable policy and schema | yes | read-only exact lookup | no | Active v1 row must match the supplied policy |
| Transaction | `app/engine_paper/unit_of_work.py` | `PaperUnitOfWork` | Sole outer transaction owner | yes | no | no | Service calls only `uow.commit()` |
| Repositories | `app/engine_paper/repositories.py` | `SimulationPolicyRepository`, `get_ingestion_graph` | Exact bounded persistence reads | yes | narrow read composition | yes | Adds only policy and ingestion-graph reads for replay/corruption proof |
| Recovery | `app/engine_paper/commit_recovery.py` | `recover_uncertain_commit` | Three fresh-session lookups | yes | no | no | No blind write replay |
| Ingestion | `app/engine_paper/command_ingestion_service.py` | request/result/service | Explicit application boundary | no | no | yes | Previously missing callable operation |
| Execution input | `app/engine_paper/order_execution_service.py` | `PaperEntryExecutionRequest` | Future one-attempt execution input | yes | no | no | Compatibility is constructed but never executed |
| Migration | `alembic/versions/0010_paper_final_approval_and_order_transition_event_vocabulary.py` | revision 0010 | Isolated event constraint authority | yes | no | no | No migration or production application |

## Admission and mapping

The immutable request contains final strategy, controlled quantity, and final
risk approvals; the exact fill policy; PAPER mode and explicit authorization;
all aggregate/event/journal identities; one UTC timestamp; and explicit
correlation/causation identities. It contains no session, credential, network
client, mutable mapping, price override, quantity override, or research-only
authority.

Admission rejects OFF, LIVE, unknown mode, missing explicit authorization,
non-current health, future data, expiry, any false final flag, every causal
link mismatch, policy absence/mismatch, and any mapper inconsistency before
opening a UoW. `paper_ingestion_command_id` binds the three final approval
identities to the persisted command identity while the existing
`PAPER_IDEMPOTENCY_VERSION = v1` command tuple remains unchanged.

## Atomic operation

One UoW performs:

```text
exact active policy lookup
-> command create-or-get plus command journal
-> ENTRY order persisted CREATED plus event/journal
-> state-machine CREATED -> VALIDATED plus event/journal
-> state-machine VALIDATED -> OPEN plus event/journal
-> complete bounded graph verification
-> one outer commit
```

Any validation, repository, transition, injected boundary, or graph failure
leaves the outer transaction uncommitted and therefore rolls back every
fragment. Exact replay first verifies the complete OPEN graph (three order
events and four journal rows) and returns without mutation. A material
collision returns `IDEMPOTENCY_CONFLICT`; a partial or corrupt graph returns
`EXISTING_GRAPH_INCONSISTENT` and is never repaired.

Uncertain commit resolution uses at most three fresh sessions. A matching
complete graph resolves committed, absence resolves not committed, a conflict
fails as idempotency conflict, and a partial graph fails as inconsistent.
There is no blind replay.

## Runtime boundary

Successful output is directly shaped for a future
`PaperEntryExecutionRequest`: command present, ENTRY/MARKET_SIMULATED order
OPEN at version 2, matching symbol/side/quantity/policy identities, and
validated/opened events present. Ingestion creates zero fills and zero
positions and does not call either the fill simulator or order execution
service.
