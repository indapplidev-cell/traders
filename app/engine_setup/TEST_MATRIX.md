# engine_setup validation matrix

| Contract | Tests |
|---|---|
| Current setup families and status routing | `tests/engine_setup/test_families_and_status.py::test_current_setup_families_route_by_existing_contract` |
| NO_SETUP, WAIT_FOR_CONFIRMATION, SETUP_INVALID, UNKNOWN/NO_ACTION safety | `test_families_and_status.py` |
| Analysis boundary, freshness, insufficient data, no mutation, determinism | `test_causality_diagnostics_quality.py::test_detector_propagates_analysis_boundary_without_mutation`, `::test_freshness_or_degraded_failure_never_creates_setup`, `::test_not_enough_data_maps_to_no_setup`, `::test_rules_are_deterministic_and_do_not_mutate_context` |
| Reasons, invalidations, missing levels and confirmation | `test_causality_diagnostics_quality.py::test_missing_levels_and_confirmation_do_not_become_candidate`, `test_families_and_status.py::test_invalid_quality_invalidates_existing_structure` |
| Structural, confirmation, context, penalties, total score and bounds | `test_causality_diagnostics_quality.py::test_quality_components_are_bounded_and_deterministic`, `::test_quality_score_boundaries_and_missing_policy`, `::test_quality_model_rejects_out_of_range_component` |
| Serialization, immutability, stable imports | `test_causality_diagnostics_quality.py::test_candidate_is_frozen_and_json_serializable`, `::test_public_imports_have_no_legacy_setup_module` |

Historical labels `SHORT_CONTINUATION_PRACTICAL_TARGET`,
`SHORT_FAILED_REBOUND`, and `TRAP_REVERSAL` are not current public enum members.
Direction is a separate `DirectionHint`; current semantic replacements are the
continuation and `FALSE_BREAKOUT_REVERSAL` families. `RANGE_BOUNDARY_REJECTION`
is current evidence that routes to `RANGE_REJECTION`.

The current quality contract intentionally has no volume, target, or RR
component: those are downstream planning concerns. The matrix locks the actual
structural/confirmation/context model without introducing a functional change.
