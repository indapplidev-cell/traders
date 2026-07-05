from app.diagnostics.label_grid_sensitivity_recompute import (
    build_current_config_mapping_audit,
    build_production_label_semantics_parity_audit,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


PRODUCTION = {
    "up_pct": 4.42,
    "down_pct": 3.19,
    "flat_pct": 92.39,
    "directional_pct": 7.61,
    "directional_count": 74,
}


def _board():
    return [
        {"flat_pct": 1.0, "directional_pct": 99.0, "diagnostic_verdict": "TOO_NOISY"},
        {"flat_pct": 9.0, "directional_pct": 91.0, "diagnostic_verdict": "TOO_NOISY"},
    ]


def _audit(**kwargs):
    return build_production_label_semantics_parity_audit(
        production_reference=kwargs.get("production_reference", PRODUCTION),
        recompute_board=kwargs.get("recompute_board", _board()),
        denominator_evidence=kwargs.get("denominator_evidence", {"candle_count": 7282}),
        current_config_id=kwargs.get(
            "current_config_id",
            "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
        ),
    )


def test_large_flat_distribution_gap_is_semantics_mismatch() -> None:
    audit = _audit()

    assert audit["read_only_recompute_current"]["verdict"] == "SEMANTICS_MISMATCH"
    assert audit["read_only_recompute_current"]["flat_pct_range"] == [1.0, 9.0]
    assert "PRODUCTION_LABEL_PARITY_NOT_PROVEN" in audit["ml38_10_40_parity_decision"]
    assert "READ_ONLY_RECOMPUTE_SEMANTICS_MISMATCH" in audit["ml38_10_40_parity_decision"]


def test_mismatched_too_noisy_board_is_not_actionable() -> None:
    audit = _audit()

    assert audit["sensitivity_board_actionability"] == "NOT_ACTIONABLE_PARITY_NOT_PROVEN"
    assert "CURRENT_SENSITIVITY_BOARD_TOO_NOISY_NOT_ACTIONABLE" in audit["decision"]


def test_semantics_gap_board_contains_required_root_causes() -> None:
    names = {row["gap_name"] for row in _audit()["label_recompute_semantics_gap_board"]}

    assert "denominator_mismatch" in names
    assert "missing_setup_quality_mask" in names
    assert "threshold_unit_mismatch" in names
    assert "timeout_flat_semantics_mismatch" in names
    assert all(row["requires_code_change_to_label_builder"] is False for row in _audit()["label_recompute_semantics_gap_board"])
    assert all(row["requires_db_write"] is False for row in _audit()["label_recompute_semantics_gap_board"])


def test_encoded_config_mapping_stays_incomplete_without_full_payload() -> None:
    mapping = build_current_config_mapping_audit(
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe"
    )

    assert mapping["mapping"]["horizon"] == 12
    assert mapping["mapping"]["direction_atr_threshold"] == 0.65
    assert mapping["mapping"]["setup_quality_mask"] == 0.60
    assert mapping["status"] == "CURRENT_CONFIG_MAPPING_INCOMPLETE"
    assert "tp_threshold" in mapping["missing_mapping_fields"]
    assert mapping["sensitivity_board_actionable"] is False


def test_audit_never_proposes_label_or_gate_changes() -> None:
    decisions = _audit()["decision"]

    assert "DO_NOT_CHANGE_LABELS_YET" in decisions
    assert "DO_NOT_CHANGE_GATES" in decisions
    assert "DO_NOT_RUN_TRAINING" in decisions
    assert not any(value.startswith("CHANGE_LABEL") or value.startswith("SOFTEN_GATE") for value in decisions)


def test_missing_compact_fields_do_not_crash_or_claim_parity() -> None:
    audit = _audit(production_reference={}, recompute_board=[], denominator_evidence={})

    assert audit["read_only_recompute_current"]["verdict"] == "PARITY_NOT_PROVEN"
    assert "PRODUCTION_LABEL_PARITY_NOT_PROVEN" in audit["decision"]
    assert "NEEDS_DENOMINATOR_ALIGNMENT" in audit["decision"]


def test_reporter_exposes_all_parity_blocks() -> None:
    audit = _audit()
    payload = {
        "production_label_semantics_parity_audit": audit,
        "label_recompute_semantics_gap_board": audit["label_recompute_semantics_gap_board"],
        "current_config_mapping_audit": audit["current_config_mapping_audit"],
        "ml38_10_40_parity_decision": audit["ml38_10_40_parity_decision"],
    }
    compact = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(payload)
    markdown = MultiSymbolFeatureRegimeReporter()._markdown(payload)

    assert compact["production_label_semantics_parity_audit"]["diagnostic_version"] == "ml38.10.40"
    assert compact["label_recompute_semantics_gap_board"]
    assert "ML38.10.40 Production Label Semantics Parity Audit" in markdown
