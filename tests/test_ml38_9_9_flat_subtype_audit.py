from app.diagnostics.flat_subtype_audit import FlatSubtypeAudit


def test_flat_subtype_audit_detects_volatile_flat() -> None:
    payload = FlatSubtypeAudit().evaluate(
        [
            {
                "future_close_atr_label": "FLAT",
                "future_move_atr": 0.35,
                "up_move_atr": 1.1,
                "down_move_atr": 0.2,
                "first_touch_ambiguous": False,
                "has_setup_context": True,
            }
        ]
    )

    assert payload["flat_subtype_counts"]["volatile_flat"] == 1
    assert payload["dominant_flat_subtype"] == "volatile_flat"
