from app.diagnostics.trap_invalidation_feature_impact_audit import TrapInvalidationFeatureImpactAudit
from app.features.feature_models import SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES


def test_ml38_10_12_trap_audit_reports_directional_feature_impact() -> None:
    feature_names = list(SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES)
    false_breakout_index = feature_names.index("schwager_false_breakout_risk_score")
    bull_trap_index = feature_names.index("schwager_bull_trap_risk_score")
    safe_index = feature_names.index("schwager_trap_safe_setup_score")

    feature_rows = []
    opportunity_probabilities = []
    opportunity_targets = []
    direction_targets = []
    direction_probabilities = []
    setup_quality_scores = []

    for _ in range(14):
        row = [0.0] * len(feature_names)
        row[false_breakout_index] = 0.10
        row[bull_trap_index] = 0.15
        row[safe_index] = 0.88
        feature_rows.append(row)
        opportunity_probabilities.append(0.80)
        opportunity_targets.append(1)
        direction_targets.append(0)
        direction_probabilities.append([0.80, 0.15, 0.05])
        setup_quality_scores.append(0.90)

    for _ in range(14):
        row = [0.0] * len(feature_names)
        row[false_breakout_index] = 0.86
        row[bull_trap_index] = 0.78
        row[safe_index] = 0.22
        feature_rows.append(row)
        opportunity_probabilities.append(0.80)
        opportunity_targets.append(0)
        direction_targets.append(2)
        direction_probabilities.append([0.55, 0.40, 0.05])
        setup_quality_scores.append(0.90)

    payload = TrapInvalidationFeatureImpactAudit().analyze(
        feature_names=feature_names,
        feature_rows=feature_rows,
        opportunity_probabilities=opportunity_probabilities,
        opportunity_targets=opportunity_targets,
        direction_targets=direction_targets,
        direction_probabilities=direction_probabilities,
        setup_quality_scores=setup_quality_scores,
        opportunity_probability_threshold=0.65,
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
    )

    assert payload["audit_status"] == "COMPLETED"
    assert payload["directional_feature_impact_status"] in {"USEFUL_DIRECTIONAL", "WEAK_DIRECTIONAL"}
    assert payload["expected_direction_feature_count"] >= 3
    assert payload["unexpected_direction_feature_count"] == 0
    assert payload["expected_direction_ratio"] == 1.0
    top_expected_names = [item["feature_name"] for item in payload["top_expected_direction_features"]]
    assert "schwager_false_breakout_risk_score" in top_expected_names
    assert "schwager_trap_safe_setup_score" in top_expected_names
    assert payload["feature_impacts"]["schwager_false_breakout_risk_score"]["expected_direction_matches"] is True
    assert payload["feature_impacts"]["schwager_trap_safe_setup_score"]["expected_direction_matches"] is True
