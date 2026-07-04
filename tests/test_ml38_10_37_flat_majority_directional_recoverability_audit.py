import pytest

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


def _candidate(
    config_id: str = "top_research_probe",
    *,
    score: float = 20.0,
    research_only: bool = True,
) -> dict:
    failed_gates = ["baseline_edge_gate", "bias_gate"]
    if research_only:
        failed_gates.append("research_only_fold_repair_probe_gate")
    return {
        "symbol": "SOLUSDT",
        "config_id": config_id,
        "candidate_status": "REJECTED",
        "score": score,
        "actual_class_distribution": {"UP": 0.0412, "DOWN": 0.0361, "FLAT": 0.9227},
        "probability_diagnostics": {
            "actual_direction_counts": {"UP": 40, "DOWN": 35, "FLAT": 898},
            "total_rows": 973,
        },
        "baseline_edge": -0.73,
        "opportunity_precision": 0.44,
        "opportunity_recall": 0.66,
        "profit_factor": 1.10,
        "profit_total_r": 3.5,
        "walk_forward_profit_factor": 1.07,
        "walk_forward_total_r": 2.7,
        "failed_gates": failed_gates,
        "research_only_total_r_repair_enabled": research_only,
    }


def _audit(*candidates: dict) -> dict:
    rows = list(candidates) or [_candidate()]
    symbol_results = [
        {
            "symbol": "SOLUSDT",
            "configs_ranked": rows,
            "actual_class_distribution": rows[0].get("actual_class_distribution", {}),
        }
    ]
    return MultiSymbolFeatureRegimeAnalyzer._flat_majority_directional_recoverability_audit(
        symbol_results, rows, rows
    )


def test_flat_majority_pressure_and_directional_math() -> None:
    audit = _audit()
    distribution = audit["label_distribution"]

    assert audit["baseline_pressure_audit"]["baseline_edge_gate_pressure"] == (
        "HIGH_FLAT_MAJORITY_PRESSURE"
    )
    assert distribution["directional_pct"] == pytest.approx(75 / 973)
    assert distribution["flat_to_directional_ratio"] == pytest.approx(898 / 75)
    assert audit["directional_sample_audit"]["directional_count"] == 75
    assert audit["directional_sample_audit"]["enough_directional_samples"] is False
    assert "FLAT_BASELINE_DOMINATES" in audit["directional_recoverability_decision"]


def test_baseline_explanation_and_top_candidate_blocker_board() -> None:
    audit = _audit(
        _candidate("first", score=20.0),
        _candidate("second", score=19.0, research_only=False),
    )
    board = audit["top_candidate_gate_blocker_board"]

    assert audit["baseline_edge_gate_explanation"]["dominant_baseline"] == (
        "always_predict_FLAT"
    )
    assert [row["config_id"] for row in board] == ["first", "second"]
    assert "baseline_edge_gate" in board[0]["failed_gates"]
    assert board[0]["rejected_because_research_only"] is True
    assert board[0]["tradable_edge"] is False
    assert board[1]["profit_factor"] > 1.0
    assert board[1]["candidate_status"] == "REJECTED"
    assert board[1]["tradable_edge"] is False


def test_missing_optional_compact_fields_use_distribution_fallback() -> None:
    candidate = {
        "symbol": "SOLUSDT",
        "config_id": "compact_only",
        "candidate_status": "REJECTED",
        "score": 1.0,
        "actual_class_distribution": {"UP": 4.0, "DOWN": 4.0, "FLAT": 92.0},
        "failed_gates": ["baseline_edge_gate"],
    }
    audit = _audit(candidate)

    assert audit["label_distribution"]["directional_pct"] == pytest.approx(0.08)
    assert audit["directional_sample_audit"]["directional_count"] is None
    assert audit["recoverability_audit"]["directional_precision_signal"] == "NOT_AVAILABLE"
    assert audit["directional_recoverability_decision"] != [
        "UNKNOWN_INSUFFICIENT_COMPACT_FIELDS"
    ]


def test_unknown_is_reserved_for_genuinely_insufficient_evidence() -> None:
    audit = MultiSymbolFeatureRegimeAnalyzer._flat_majority_directional_recoverability_audit(
        [{"symbol": "SOLUSDT"}], [], []
    )
    assert audit["directional_recoverability_decision"] == [
        "UNKNOWN_INSUFFICIENT_COMPACT_FIELDS"
    ]


def test_reporter_exposes_new_top_level_blocks() -> None:
    audit = _audit()
    payload = {
        "flat_majority_directional_recoverability_audit": audit,
        "baseline_edge_gate_explanation": audit["baseline_edge_gate_explanation"],
        "top_candidate_gate_blocker_board": audit["top_candidate_gate_blocker_board"],
        "directional_recoverability_decision": audit["directional_recoverability_decision"],
    }
    compact = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(payload)
    markdown = MultiSymbolFeatureRegimeReporter()._markdown(payload)

    assert compact["baseline_edge_gate_explanation"]
    assert compact["top_candidate_gate_blocker_board"][0]["failed_gates"]
    assert "ML38.10.37 FLAT-majority Directional Recoverability Audit" in markdown
    assert "top_research_probe" in markdown
