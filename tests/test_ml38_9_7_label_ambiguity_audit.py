from types import SimpleNamespace

from app.diagnostics.label_ambiguity_audit import LabelAmbiguityAudit


def test_label_ambiguity_audit_handles_empty_rows() -> None:
    payload = LabelAmbiguityAudit().evaluate([])

    assert payload["diagnostic_name"] == "label_ambiguity_audit"
    assert payload["label_noise_rating"] == "UNAVAILABLE"


def test_label_ambiguity_audit_detects_volatile_flat() -> None:
    rows = [
        SimpleNamespace(direction_label="FLAT", max_favorable_move_atr=1.1, max_adverse_move_atr=0.9, tp_before_sl=None),
        {"direction_label": "UP", "max_favorable_move_atr": 0.9, "max_adverse_move_atr": 0.2},
    ]

    payload = LabelAmbiguityAudit().evaluate(rows)

    assert payload["row_count"] == 2
    assert payload["volatile_flat_count"] == 1
    assert payload["ambiguous_row_count"] >= 1
    assert payload["recommendation"] in {
        "split_flat_subtypes_or_no_trade",
        "consider_first_touch_or_setup_aware_labels",
    }

