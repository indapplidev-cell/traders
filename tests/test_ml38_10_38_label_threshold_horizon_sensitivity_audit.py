import pytest

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


def _audit(
    *,
    up: float = 0.0442,
    down: float = 0.0319,
    flat: float = 0.9239,
    up_count: int | None = 43,
    down_count: int | None = 31,
) -> dict:
    directional_count = (
        None if up_count is None or down_count is None else up_count + down_count
    )
    prior = {
        "label_distribution": {
            "up_pct": up,
            "down_pct": down,
            "flat_pct": flat,
            "directional_pct": up + down,
            "flat_to_directional_ratio": flat / (up + down),
        },
        "directional_sample_audit": {
            "up_count": up_count,
            "down_count": down_count,
            "directional_count": directional_count,
        },
    }
    return MultiSymbolFeatureRegimeAnalyzer._label_threshold_horizon_sensitivity_audit(
        prior, []
    )


def test_flat_pressure_sample_warning_and_ratio() -> None:
    audit = _audit()

    assert audit["current_parameter_pressure"]["flat_majority_pressure"] == "HIGH"
    assert audit["current_parameter_pressure"]["sample_warning"] == (
        "directional_sample_below_100"
    )
    assert audit["current_label_distribution"]["directional_count"] == 74
    assert audit["current_label_distribution"]["flat_to_directional_ratio"] == pytest.approx(
        0.9239 / 0.0761
    )


def test_recoverability_requirements_and_plan_are_diagnostic_only() -> None:
    audit = _audit()

    requirements = audit["label_recoverability_requirements"]
    assert requirements["minimum_directional_count_quick_quality"] == 100
    assert requirements["diagnostic_only"] is True
    assert "research_only" in requirements["candidate_exclusion"]
    assert all(row["diagnostic_only"] is True for row in audit["next_label_diagnostic_plan"])
    assert not any(
        "soften" in row["action"] or "accept_research" in row["action"]
        for row in audit["next_label_diagnostic_plan"]
    )


def test_decisions_never_soften_gates_or_accept_research_only() -> None:
    decisions = _audit()["ml38_10_38_label_audit_decision"]

    assert "DO_NOT_CHANGE_GATES" in decisions
    assert "DO_NOT_ACCEPT_RESEARCH_ONLY_CANDIDATE" in decisions
    assert not any("SOFTEN" in value and "DO_NOT" not in value for value in decisions)


def test_missing_compact_fields_use_honest_fallback_without_crash() -> None:
    audit = MultiSymbolFeatureRegimeAnalyzer._label_threshold_horizon_sensitivity_audit(
        {}, [{}]
    )

    assert audit["status"] == "INSUFFICIENT_COMPACT_FIELDS_FOR_FULL_RECOMPUTE"
    assert audit["sensitivity_board"]
    assert all(
        row["diagnostic_verdict"] == "INSUFFICIENT_DATA"
        for row in audit["sensitivity_board"]
    )
    assert audit["required_fields_for_full_recompute"]
    assert audit["read_only_extractor_required"]


def test_complete_precomputed_rows_are_preserved() -> None:
    row = {
        "horizon": 8,
        "tp_threshold": 0.8,
        "sl_threshold": 0.8,
        "flat_boundary": 0.2,
        "up_pct": 8.0,
        "down_pct": 7.0,
        "flat_pct": 85.0,
        "directional_pct": 15.0,
        "directional_count": 146,
        "up_down_balance": 0.875,
        "flat_to_directional_ratio": 85 / 15,
        "label_noise_risk": "MEDIUM",
        "expected_baseline_pressure": "MEDIUM",
        "diagnostic_verdict": "PROMISING_DIAGNOSTIC_ZONE",
    }
    audit = MultiSymbolFeatureRegimeAnalyzer._label_threshold_horizon_sensitivity_audit(
        {}, [{"label_threshold_horizon_sensitivity_rows": [row]}]
    )

    assert audit["status"] == "COMPUTED_FROM_COMPACT_SENSITIVITY_ROWS"
    assert audit["sensitivity_board"][0]["diagnostic_verdict"] == (
        "PROMISING_DIAGNOSTIC_ZONE"
    )


def test_reporter_exposes_ml38_10_38_blocks() -> None:
    audit = _audit()
    payload = {
        "label_threshold_horizon_sensitivity_audit": audit,
        "label_recoverability_requirements": audit["label_recoverability_requirements"],
        "next_label_diagnostic_plan": audit["next_label_diagnostic_plan"],
        "ml38_10_38_label_audit_decision": audit["ml38_10_38_label_audit_decision"],
    }

    compact = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(payload)
    markdown = MultiSymbolFeatureRegimeReporter()._markdown(payload)

    assert compact["label_threshold_horizon_sensitivity_audit"]["diagnostic_version"] == (
        "ml38.10.38"
    )
    assert compact["label_recoverability_requirements"]
    assert "ML38.10.38 Label Threshold / Horizon Sensitivity Audit" in markdown
    assert "DO_NOT_CHANGE_GATES" in markdown
