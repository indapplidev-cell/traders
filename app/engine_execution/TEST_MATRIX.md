# ENGINE-EXECUTION-01 requirements-to-test matrix

Status for every row is `COVERED`. Parameterized tests may provide multiple cases under one
test name.

| ID | Requirement | Test file | Test name | Status |
|---:|---|---|---|---|
| 1 | APPROVED + RISK_APPROVED produces READY | `tests/engine_execution/test_builder_validation.py` | `test_approved_strategy_and_risk_create_ready_intent` | COVERED |
| 2 | Rejected strategy cannot produce READY | `tests/engine_execution/test_builder_validation.py` | `test_rejected_strategy_is_not_ready` | COVERED |
| 3 | Rejected risk cannot produce READY | `tests/engine_execution/test_builder_validation.py` | `test_rejected_risk_is_not_ready` | COVERED |
| 4 | LIVE is always blocked | `tests/engine_execution/test_builder_validation.py` | `test_live_is_always_disabled` | COVERED |
| 5 | PAPER is allowed | `tests/engine_execution/test_builder_validation.py` | `test_paper_and_dry_run_are_allowed` | COVERED |
| 6 | DRY_RUN is allowed | `tests/engine_execution/test_builder_validation.py` | `test_paper_and_dry_run_are_allowed` | COVERED |
| 7 | Quantity less than or equal to zero is rejected | `tests/engine_execution/test_builder_validation.py` | `test_non_positive_quantity_is_rejected` | COVERED |
| 8 | NaN and infinity are rejected | `tests/engine_execution/test_builder_validation.py` | `test_nan_and_infinity_are_rejected` | COVERED |
| 9 | Invalid LONG stop is rejected | `tests/engine_execution/test_builder_validation.py` | `test_wrong_stop_for_long_and_short` | COVERED |
| 10 | Invalid SHORT stop is rejected | `tests/engine_execution/test_builder_validation.py` | `test_wrong_stop_for_long_and_short` | COVERED |
| 11 | Invalid LONG target is rejected | `tests/engine_execution/test_builder_validation.py` | `test_wrong_target_for_long_and_short` | COVERED |
| 12 | Invalid SHORT target is rejected | `tests/engine_execution/test_builder_validation.py` | `test_wrong_target_for_long_and_short` | COVERED |
| 13 | Symbol mismatch is rejected | `tests/engine_execution/test_builder_validation.py` | `test_symbol_and_side_mismatches_are_rejected` | COVERED |
| 14 | Side mismatch is rejected | `tests/engine_execution/test_builder_validation.py` | `test_symbol_and_side_mismatches_are_rejected` | COVERED |
| 15 | An unclosed source window is rejected | `tests/engine_execution/test_builder_validation.py` | `test_unclosed_or_missing_window_is_rejected` | COVERED |
| 16 | Idempotency key is deterministic | `tests/engine_execution/test_idempotency.py` | `test_idempotency_ignores_timestamp_and_metadata` | COVERED |
| 17 | Repeated intent is DUPLICATE | `tests/engine_execution/test_builder_validation.py` | `test_idempotency_is_deterministic_and_duplicate_is_marked` | COVERED |
| 18 | Canonical JSON is stable | `tests/engine_execution/test_serialization.py` | `test_canonical_json_is_stable_and_round_trip_preserves_intent` | COVERED |
| 19 | Serialization round trip preserves values | `tests/engine_execution/test_serialization.py` | `test_canonical_json_is_stable_and_round_trip_preserves_intent` | COVERED |
| 20 | DryRun gateway performs no network operation | `tests/engine_execution/test_gateways.py` | `test_dry_run_acknowledges_locally` | COVERED |
| 21 | Paper gateway delegates only to engine_paper | `tests/engine_execution/test_gateways.py` | `test_paper_gateway_delegates_only_to_engine_paper` | COVERED |
| 22 | DisabledLive gateway always blocks | `tests/engine_execution/test_gateways.py` | `test_disabled_live_gateway_always_rejects` | COVERED |
| 23 | No private Binance imports | `tests/engine_execution/test_static_safety.py` | `test_runtime_ast_has_no_network_container_or_process_imports`; `test_runtime_import_boundary_allows_only_engine_paper_project_adapter` | COVERED |
| 24 | No credential reading | `tests/engine_execution/test_static_safety.py` | `test_runtime_ast_has_no_private_exchange_or_credential_operations` | COVERED |
| 25 | No Docker SDK | `tests/engine_execution/test_static_safety.py` | `test_runtime_ast_has_no_network_container_or_process_imports` | COVERED |
| 26 | CLI LIVE returns non-zero | `tests/engine_execution/test_cli.py` | `test_cli_live_returns_nonzero_disabled_json` | COVERED |
| 27 | CLI PAPER and DRY_RUN return valid JSON | `tests/engine_execution/test_cli.py` | `test_cli_safe_modes_return_ready_json` | COVERED |
| 28 | Existing risk and paper suites do not regress | `tests/test_engine_risk_01_runner.py`; `tests/test_engine_paper_01_runner.py` | `test_runner_accepts_only_strategy_decision`; `test_runner_accepts_only_risk_decisions_and_supports_async_iteration` plus complete selected suites | COVERED |

## FIX-01 additional acceptance coverage

| ID | Requirement | Test file | Test name | Status |
|---:|---|---|---|---|
| A1 | Correct package init and public exports | `tests/engine_execution/test_package_contract.py` | `test_package_import_and_public_exports_are_valid` | COVERED |
| A2 | Stray init names are absent | `tests/engine_execution/test_package_contract.py` | `test_correct_dunder_init_exists_and_stray_names_are_absent` | COVERED |
| A3 | Research-only approval scope | `tests/engine_execution/test_approval_policy.py` | `test_research_approval_pair_is_safe_mode_only` | COVERED |
| A4 | Research approval never authorizes LIVE | `tests/engine_execution/test_approval_policy.py` | `test_research_statuses_never_authorize_live` | COVERED |
| A5 | Mixed approval pairs are rejected | `tests/engine_execution/test_approval_policy.py` | `test_mixed_approval_pairs_are_contract_mismatch` | COVERED |
| A6 | LIVE is the first safety gate | `tests/engine_execution/test_approval_policy.py` | `test_live_gate_is_first_even_with_other_invalid_input` | COVERED |
| A7 | Deep immutable intent and acknowledgement | `tests/engine_execution/test_immutability.py` | `test_execution_intent_is_deeply_immutable`; `test_acknowledgement_is_deeply_immutable` | COVERED |
| A8 | Concurrent duplicate registration | `tests/engine_execution/test_idempotency.py` | `test_registry_marks_only_one_concurrent_build_as_new` | COVERED |
| A9 | Duplicate does not call PaperRunner twice | `tests/engine_execution/test_gateways.py` | `test_paper_gateway_does_not_run_same_ready_intent_twice` | COVERED |
| A10 | Rejected/disabled intent never reaches PaperRunner | `tests/engine_execution/test_gateways.py` | `test_paper_gateway_does_not_run_rejected_or_disabled_intent` | COVERED |
| A11 | PaperRunner exception is safely rejected | `tests/engine_execution/test_gateways.py` | `test_paper_runner_exception_becomes_safe_rejection` | COVERED |
| A12 | CLI malformed inputs have safe JSON errors | `tests/engine_execution/test_cli.py` | `test_cli_invalid_json_is_safe_json_error`; `test_cli_missing_file_is_safe_json_error`; `test_cli_missing_required_field_is_safe_json_error` | COVERED |
| A13 | Runtime AST safety boundary | `tests/engine_execution/test_static_safety.py` | `test_runtime_ast_has_no_network_container_or_process_imports`; `test_runtime_import_boundary_allows_only_engine_paper_project_adapter` | COVERED |
