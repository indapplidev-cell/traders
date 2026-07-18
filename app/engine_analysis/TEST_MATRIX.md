# engine_analysis validation matrix

This matrix covers the recovered current contract. Every test uses finalized,
repository-local data and requires no network, database, Docker, or wall clock.

| Contract | Tests |
|---|---|
| Closed-candle causality, boundary, higher-TF close, no mutation | `test_causality.py` |
| HH/HL, LH/LL, sideways, insufficient pivots | `test_structure_and_regime.py::test_hh_hl_lh_ll_and_sideways_structure`, `::test_insufficient_pivots_are_unknown` |
| UP, DOWN, FLAT, UNKNOWN and conservative fallback | `test_structure_and_regime.py::test_composer_covers_all_public_regimes`, `::test_no_confirmed_hypothesis_has_conservative_reason` |
| Conflict resolution and stable reason codes | `test_structure_and_regime.py::test_conflict_resolver_prefers_structure_without_action` |
| Impulse/entry, structure, zone and conflict diagnostics | `test_quality_online_and_contract.py::test_impulse_quality_diagnostics_are_causal_and_serializable`, `::test_market_structure_diagnostics_report_observed_boundary`, `::test_zone_and_conflict_diagnostics_remain_non_actionable` |
| Online adapter identity/boundary and degraded gating | `test_quality_online_and_contract.py::test_online_adapter_propagates_identity_boundary_and_serialization`, `::test_invalid_or_degraded_online_input_is_gated` |
| Serialization, immutable models, enums, public imports, no legacy import | `test_quality_online_and_contract.py::test_public_models_are_frozen_and_json_round_trip`, `::test_stable_public_imports_and_no_legacy_package` |
| Missing quality never becomes actionable | `test_quality_online_and_contract.py::test_analysis_snapshot_missing_quality_is_not_actionable` |

The historical per-stage test filenames are replaced by this contract-focused
matrix; their mapping is recorded in the external recovery closure bundle.
