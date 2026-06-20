from app.diagnostics.trap_invalidation_feature_impact_audit import TrapInvalidationFeatureImpactAudit
from app.features.feature_models import SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES


def test_trap_invalidation_feature_impact_audit_separates_false_positive_rows() -> None:
    feature_names = list(SCHWAGER_TRAP_INVALIDATION_FEATURE_NAMES)
    risk_index = feature_names.index("schwager_false_breakout_risk_score")
    safe_index = feature_names.index("schwager_trap_safe_setup_score")

    feature_rows = []
    opportunity_probabilities = []
    opportunity_targets = []
    direction_targets = []
    direction_probabilities = []
    setup_quality_scores = []

    for _ in range(12):
        row = [0.0] * len(feature_names)
        row[risk_index] = 0.10
        row[safe_index] = 0.85
        feature_rows.append(row)
        opportunity_probabilities.append(0.80)
        opportunity_targets.append(1)
        direction_targets.append(0)
        direction_probabilities.append([0.80, 0.15, 0.05])
        setup_quality_scores.append(0.90)

    for _ in range(12):
        row = [0.0] * len(feature_names)
        row[risk_index] = 0.90
        row[safe_index] = 0.20
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
    assert payload["feature_impact_status"] in {"USEFUL", "WEAK_BUT_PRESENT"}
    assert payload["group_counts"]["true_positive"] == 12
    assert payload["group_counts"]["false_positive"] == 12
    top_names = [item["feature_name"] for item in payload["top_separating_features"]]
    assert "schwager_false_breakout_risk_score" in top_names
    assert payload["feature_impacts"]["schwager_false_breakout_risk_score"]["false_positive_minus_true_positive_mean"] > 0
