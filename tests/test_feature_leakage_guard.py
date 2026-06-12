import json

from app.diagnostics.feature_leakage_guard import FeatureLeakageGuard


def test_feature_leakage_guard_accepts_normal_features() -> None:
    payload = FeatureLeakageGuard().check(["trend_strength", "volume_ratio_20", "ema_21_to_ema_50"])

    assert payload["leakage_risk_detected"] is False
    assert payload["suspicious_features"] == []
    assert json.dumps(payload)


def test_feature_leakage_guard_detects_suspicious_features() -> None:
    payload = FeatureLeakageGuard().check(["trend_strength", "future_return", "next_move", "target_score"])

    assert payload["leakage_risk_detected"] is True
    assert "future_return" in payload["suspicious_features"]
    assert "next_move" in payload["suspicious_features"]
    assert "target_score" in payload["suspicious_features"]
    assert json.dumps(payload)
