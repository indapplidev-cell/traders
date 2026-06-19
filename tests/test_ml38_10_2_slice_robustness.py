from app.diagnostics.schwager_robustness_decision_board import (
    build_schwager_slice_robustness,
)


def test_slice_robustness_reports_edge_by_requested_dimensions() -> None:
    rows = [
        _row("UP", "UP", "trend_up", trend_strength=0.9, breakout_strength=0.5, atr_14=1.7),
        _row("UP", "UP", "trend_up", trend_strength=0.8, breakout_strength=0.5, atr_14=1.6),
        _row("UP", "UP", "trend_up", trend_strength=0.7, breakout_strength=0.5, atr_14=1.5),
        _row("DOWN", "UP", "range", trend_strength=0.1, doji_score=0.8, atr_14=0.7),
        _row("DOWN", "UP", "range", trend_strength=0.1, doji_score=0.8, atr_14=0.7),
        _row("DOWN", "UP", "range", trend_strength=0.1, doji_score=0.8, atr_14=0.7),
        _row("FLAT", "UP", "low_volatility", trend_strength=0.0, near_support=True, atr_14=0.4),
        _row("FLAT", "UP", "low_volatility", trend_strength=0.0, near_support=True, atr_14=0.4),
        _row("FLAT", "UP", "low_volatility", trend_strength=0.0, near_support=True, atr_14=0.4),
    ]

    payload = build_schwager_slice_robustness(rows, label_mode="first_touch")

    assert payload["diagnostic_name"] == "schwager_slice_robustness"
    assert "edge_by_time_slice" in payload
    assert "edge_by_regime" in payload
    assert "edge_by_setup_type" in payload
    assert "edge_by_label_mode" in payload
    assert "edge_by_opportunity_bucket" in payload
    assert "edge_by_volatility_bucket" in payload
    assert "edge_by_support_resistance_context" in payload
    assert "negative_edge_slice_detected" in payload["robustness_flags"]


def _row(
    actual_label: str,
    predicted_label: str,
    regime_name: str,
    **features: float | bool,
) -> dict[str, object]:
    payload = {
        "features_json": {
            "regime_trend_up": 1.0 if regime_name == "trend_up" else 0.0,
            "regime_range": 1.0 if regime_name == "range" else 0.0,
            "regime_low_volatility": 1.0 if regime_name == "low_volatility" else 0.0,
            "regime_high_volatility": 1.0 if regime_name == "high_volatility" else 0.0,
        }
    }
    payload["features_json"].update(features)
    payload.update(
        {
            "actual_label": actual_label,
            "predicted_label": predicted_label,
            "future_move_atr": 1.1 if actual_label != "FLAT" else 0.2,
            "max_favorable_move_atr": 1.2 if actual_label != "FLAT" else 0.2,
            "max_adverse_move_atr": 0.3 if actual_label == predicted_label else 1.0,
            "tp_before_sl": actual_label == predicted_label and actual_label != "FLAT",
        }
    )
    return payload

