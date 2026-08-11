# Future PAPER reporting capability matrix

Future principal: `traders_readonly_api`. This is a plan only; this task does not alter a role or grant.

| resource | SELECT required | reason | endpoint |
|---|---|---|---|
| `alembic_version` | yes | schema readiness gate | `/api/v1/paper/readiness` and all DB-backed routes |
| `paper_account_baselines` | yes | immutable opening balance | readiness, account, reconciliation |
| `paper_positions` | yes | bounded lifecycle and closed-trade source | positions, trades, account, reconciliation |
| `paper_orders` | yes | bounded position detail links | position detail |
| `paper_fills` | yes | authoritative persisted fees and prices | trades, account, reconciliation |
| `paper_exit_evaluation_cursors` | yes | bounded position detail status | position detail |
| `paper_exit_decisions` | yes | bounded position detail decision | position detail |
| `paper_journal_entries` | yes | authoritative lifecycle causality and bounded event summary | position detail, trades, reconciliation |
| `paper_execution_commands` | no | no reporting field requires command payload | none |
| `paper_order_events` | no | journal summary supplies the bounded lifecycle view | none |
| `paper_simulation_policies` | no | policy internals are outside desktop reporting scope | none |

No write, schema ownership, administration, or control-plane capability is planned.
