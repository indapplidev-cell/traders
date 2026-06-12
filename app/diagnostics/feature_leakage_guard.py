from __future__ import annotations

from typing import Any


FEATURE_LEAKAGE_GUARD_NAME = "feature_leakage_guard"
FEATURE_LEAKAGE_GUARD_VERSION = "ml32"
SUSPICIOUS_TOKENS = (
    "future",
    "target",
    "label",
    "next",
    "tomorrow",
    "profit_after",
    "return_future",
)


class FeatureLeakageGuard:
    """Detect obvious future-looking or target-like feature names."""

    def check(self, feature_names: list[str]) -> dict[str, Any]:
        normalized_names = [str(name) for name in feature_names]
        suspicious_features = [
            name
            for name in normalized_names
            if any(token in name.lower() for token in SUSPICIOUS_TOKENS)
        ]
        leakage_risk_detected = bool(suspicious_features)
        warnings = ["suspicious_feature_names_detected"] if leakage_risk_detected else []
        recommendations = (
            ["Remove or rename suspicious features before training."]
            if leakage_risk_detected
            else ["No obvious name-based leakage markers were found."]
        )
        return {
            "guard_name": FEATURE_LEAKAGE_GUARD_NAME,
            "guard_version": FEATURE_LEAKAGE_GUARD_VERSION,
            "checked_features": len(normalized_names),
            "suspicious_features": suspicious_features,
            "leakage_risk_detected": leakage_risk_detected,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def check_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        features_key: str = "features_json",
    ) -> dict[str, Any]:
        feature_names: set[str] = set()
        for row in rows:
            feature_names.update(str(name) for name in dict(row.get(features_key, {})).keys())
        return self.check(sorted(feature_names))
