# engine_strategy validation matrix

| Contract | Tests |
|---|---|
| Approved research plan and mandatory risk review | `tests/engine_strategy/test_decision_contract.py::test_approved_current_setup_requires_risk_review` |
| Rejected invalid setup, NO_ACTION/UNKNOWN safety | `::test_invalid_setup_is_rejected_with_stable_reason`, `::test_no_setup_and_unknown_quality_never_approve` |
| Unsupported direction/family rejection | `::test_unsupported_direction_or_family_is_rejected` |
| Stable reasons and warning propagation | `::test_conflict_warnings_propagate_to_rejection` |
| Determinism and no mutation | `::test_decision_is_deterministic_except_creation_time_and_does_not_mutate` |
| Serialization, immutability, setup boundary propagation | `::test_serialization_round_trip_immutability_and_boundary` |
| No network, database, Docker, or legacy runtime access | `::test_strategy_source_has_no_network_database_or_docker_access`, `::test_no_legacy_strategy_import` |

The current statuses are `ALLOW_RESEARCH_TRADE_PLAN`, `REJECT`, `WAIT`,
`NO_DECISION`, and `ERROR`; “APPROVED/REJECTED” in the recovery inventory map
to the first two current contract values. All outputs remain non-executable.
