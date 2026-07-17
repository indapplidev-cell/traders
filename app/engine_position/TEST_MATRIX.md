# ENGINE-POSITION-01 Test Matrix

`TEST_MATRIX_COVERAGE = 76/76`

| ID | Requirement | Test file | Test name | Status |
|---:|---|---|---|---|
| 1 | PAPER create | test_builder_contract.py | test_01_acknowledged_paper_creates_position | PASS |
| 2 | DRY_RUN create | test_builder_contract.py | test_02_acknowledged_dry_run_creates_position | PASS |
| 3 | LIVE first gate | test_builder_contract.py | test_03_live_is_blocked_first | PASS |
| 4 | Intent READY | test_builder_contract.py | test_04_intent_not_ready | PASS |
| 5 | Ack ACKNOWLEDGED | test_builder_contract.py | test_05_ack_not_acknowledged | PASS |
| 6 | Intent/ack ID | test_builder_contract.py | test_06_intent_ack_id_mismatch | PASS |
| 7 | Idempotency match | test_builder_contract.py | test_07_idempotency_mismatch | PASS |
| 8 | Mode match | test_builder_contract.py | test_08_mode_mismatch | PASS |
| 9 | Symbol match | test_builder_contract.py | test_09_symbol_mismatch | PASS |
| 10 | BUY to LONG | test_builder_contract.py | test_10_buy_maps_long | PASS |
| 11 | SELL to SHORT | test_builder_contract.py | test_11_sell_maps_short | PASS |
| 12 | Positive quantity | test_builder_contract.py | test_12_non_positive_quantity | PASS |
| 13 | Finite entry | test_builder_contract.py | test_13_non_finite_entry_price | PASS |
| 14 | Source window present | test_builder_contract.py | test_14_missing_source_window | PASS |
| 15 | Source window closed | test_builder_contract.py | test_15_unclosed_source_window | PASS |
| 16 | LONG geometry | test_builder_contract.py | test_16_invalid_long_geometry | PASS |
| 17 | SHORT geometry | test_builder_contract.py | test_17_invalid_short_geometry | PASS |
| 18 | Pending to open | test_lifecycle.py | test_18_pending_open_to_open | PASS |
| 19 | Open to partial | test_lifecycle.py | test_19_open_to_partially_closed | PASS |
| 20 | Open to closed | test_lifecycle.py | test_20_open_to_closed | PASS |
| 21 | Partial to closed | test_lifecycle.py | test_21_partial_to_closed | PASS |
| 22 | Closed cannot open | test_lifecycle.py | test_22_closed_to_open_blocked | PASS |
| 23 | Cancelled cannot open | test_lifecycle.py | test_23_cancelled_to_open_blocked | PASS |
| 24 | Rejected terminal | test_lifecycle.py | test_24_rejected_to_open_blocked_by_terminal_contract | PASS |
| 25 | Duplicate event | test_lifecycle.py | test_25_duplicate_event_blocked | PASS |
| 26 | Position ID match | test_lifecycle.py | test_26_wrong_position_id_blocked | PASS |
| 27 | Event time order | test_lifecycle.py | test_27_out_of_order_event_blocked | PASS |
| 28 | Terminal event | test_lifecycle.py | test_28_post_terminal_event_blocked | PASS |
| 29 | LONG unrealized profit | test_pnl.py | test_29_long_unrealized_profit | PASS |
| 30 | LONG unrealized loss | test_pnl.py | test_30_long_unrealized_loss | PASS |
| 31 | SHORT unrealized profit | test_pnl.py | test_31_short_unrealized_profit | PASS |
| 32 | SHORT unrealized loss | test_pnl.py | test_32_short_unrealized_loss | PASS |
| 33 | LONG realized profit | test_pnl.py | test_33_long_realized_profit | PASS |
| 34 | LONG realized loss | test_pnl.py | test_34_long_realized_loss | PASS |
| 35 | SHORT realized profit | test_pnl.py | test_35_short_realized_profit | PASS |
| 36 | SHORT realized loss | test_pnl.py | test_36_short_realized_loss | PASS |
| 37 | Fees and net | test_pnl.py | test_37_fees_reduce_net_realized | PASS |
| 38 | Partial quantity | test_pnl.py | test_38_partial_close_reduces_open_quantity | PASS |
| 39 | Over-close | test_pnl.py | test_39_over_close_is_blocked | PASS |
| 40 | Closed unrealized | test_pnl.py | test_40_closed_unrealized_is_zero | PASS |
| 41 | Decimal precision | test_pnl.py | test_41_decimal_precision_is_preserved | PASS |
| 42 | Stable average entry | test_pnl.py | test_42_average_entry_is_stable_after_close | PASS |
| 43 | Deterministic key | test_store_idempotency.py | test_43_position_key_is_deterministic | PASS |
| 44 | Key excludes volatile data | test_store_idempotency.py | test_44_position_key_ignores_timestamp_and_metadata | PASS |
| 45 | Different intent keys | test_store_idempotency.py | test_45_different_intents_have_different_keys | PASS |
| 46 | Duplicate create | test_store_idempotency.py | test_46_duplicate_position_is_rejected | PASS |
| 47 | Concurrent create | test_store_idempotency.py | test_47_concurrent_create_has_one_winner | PASS |
| 48 | Thread safety | test_store_idempotency.py | test_48_store_thread_safe_updates | PASS |
| 49 | Store event dedupe | test_store_idempotency.py | test_49_store_duplicate_event_not_applied | PASS |
| 50 | Immutable return | test_store_idempotency.py | test_50_store_returns_deep_immutable_copy | PASS |
| 51 | Position round-trip | test_serialization.py | test_51_position_round_trip | PASS |
| 52 | Fill round-trip | test_serialization.py | test_52_fill_event_round_trip | PASS |
| 53 | Other events round-trip | test_serialization.py | test_53_mark_close_cancel_event_round_trip | PASS |
| 54 | Result round-trip | test_serialization.py | test_54_transition_result_round_trip | PASS |
| 55 | Stable canonical JSON | test_serialization.py | test_55_canonical_json_is_stable | PASS |
| 56 | Decimal and UTC encoding | test_serialization.py | test_56_decimal_serializes_as_string_and_utc_as_z | PASS |
| 57 | Schema rejection | test_serialization.py | test_57_unknown_schema_is_rejected | PASS |
| 58 | Deep immutability | test_serialization.py | test_58_models_and_nested_metadata_are_immutable | PASS |
| 59 | CLI PAPER | test_cli.py | test_59_cli_paper | PASS |
| 60 | CLI DRY_RUN | test_cli.py | test_60_cli_dry_run | PASS |
| 61 | CLI LIVE | test_cli.py | test_61_cli_live_is_nonzero_and_blocked | PASS |
| 62 | CLI invalid mode | test_cli.py | test_62_cli_invalid_mode_is_safe_json | PASS |
| 63 | CLI invalid JSON | test_cli.py | test_63_cli_invalid_json | PASS |
| 64 | CLI missing file | test_cli.py | test_64_cli_missing_file | PASS |
| 65 | CLI missing field | test_cli.py | test_65_cli_missing_field | PASS |
| 66 | CLI non-finite | test_cli.py | test_66_cli_non_finite_value | PASS |
| 67 | CLI JSON stdout | test_cli.py | test_67_cli_stdout_contains_only_one_json_document | PASS |
| 68 | CLI no writes | test_cli.py | test_68_cli_creates_no_reports_or_artifacts | PASS |
| 69 | No network | test_static_safety.py | test_69_no_network_imports | PASS |
| 70 | No Docker/process | test_static_safety.py | test_70_no_docker_or_subprocess | PASS |
| 71 | No credentials | test_static_safety.py | test_71_no_credentials | PASS |
| 72 | No DB | test_static_safety.py | test_72_no_database_imports | PASS |
| 73 | No private Binance | test_static_safety.py | test_73_no_private_binance_calls | PASS |
| 74 | Execution import regression | test_static_safety.py | test_74_engine_execution_regression_import | PASS |
| 75 | Paper import regression | test_static_safety.py | test_75_engine_paper_regression_import | PASS |
| 76 | Full pytest verification | external command | `.venv\\Scripts\\python.exe -m pytest -q` | PASS |
