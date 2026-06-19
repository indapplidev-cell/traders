from types import SimpleNamespace

from app.diagnostics.setup_context_audit import SetupContextAudit


def test_setup_context_audit_handles_empty_rows() -> None:
    payload = SetupContextAudit().evaluate([])

    assert payload["diagnostic_name"] == "setup_context_audit"
    assert payload["setup_group_count"] == 0


def test_setup_context_audit_groups_nison_and_altunina_like_rows() -> None:
    rows = [
        SimpleNamespace(
            direction_label="UP",
            predicted_label="UP",
            features_json={
                "trend_strength": 0.9,
                "volume_ratio_20": 1.4,
                "hammer_score": 0.8,
                "support_distance_atr": 0.2,
                "rsi_14": 58.0,
                "breakout_strength": 0.5,
            },
        ),
        {
            "direction_label": "DOWN",
            "predicted_label": "UP",
            "features_json": {
                "trend_strength": 0.8,
                "volume_ratio_20": 1.3,
                "breakout_strength": 0.55,
                "resistance_distance_atr": 0.2,
                "shooting_star_score": 0.7,
                "rsi_14": 74.0,
            },
        },
    ]

    payload = SetupContextAudit().evaluate(rows)

    assert payload["setup_group_count"] > 0
    assert "nison_reversal_candidate" in payload["groups"]
    assert "breakout_with_volume" in payload["groups"]
    assert payload["groups"]["nison_reversal_candidate"]["row_count"] >= 1

