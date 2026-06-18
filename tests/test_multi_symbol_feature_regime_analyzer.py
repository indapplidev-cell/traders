import json
from pathlib import Path

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _write_summary(
    root: Path,
    *,
    experiment_id: str,
    symbol: str,
    score: float,
    edge: float,
    profit_factor: float,
    walk_forward_profit_factor: float,
    failed_gates: list[str],
    real_feature_diagnostics_used: bool,
    row_count: int,
    regime_features_attached: bool,
) -> Path:
    experiment_dir = root / experiment_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": experiment_id,
        "symbol": symbol,
        "interval": "15m",
        "start_date": "2025-01-01",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv2_h08_thr04_tp10_sl10",
        "best_candidate_score": score,
        "feature_version_used": "fv2",
        "real_feature_diagnostics_used": real_feature_diagnostics_used,
        "real_feature_diagnostics_row_count": row_count,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": regime_features_attached,
        "regime_specific_training_applied": False,
        "warnings": [] if real_feature_diagnostics_used else ["dataset_rows_unavailable"],
        "candidate_results": [
            {
                "config_id": "lv2_h08_thr04_tp10_sl10",
                "candidate_status": "CANDIDATE_REJECTED",
                "score": score,
                "model_accuracy": 0.41,
                "baseline_accuracy": 0.39,
                "accuracy_edge": edge,
                "baseline_edge": edge,
                "baseline_edge_status": "STRONG_EDGE" if edge > 0 else "NEGATIVE_EDGE",
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "collapse_severity": "WATCH",
                "profit_factor": profit_factor,
                "profit_total_r": -10.0,
                "walk_forward_profit_factor": walk_forward_profit_factor,
                "walk_forward_global_total_r": -20.0,
                "failed_gates": failed_gates,
                "passed_gates": ["gap_quality_gate"],
                "warnings": [],
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv2_h08_thr04_tp10_sl10",
                "candidate_status": "REJECTED",
                "score": score,
                "accuracy": 0.41,
                "baseline_accuracy": 0.39,
                "baseline_edge": edge,
                "baseline_edge_status": "STRONG_EDGE" if edge > 0 else "NEGATIVE_EDGE",
                "collapse_severity": "WATCH",
                "failed_gates": failed_gates,
                "passed_gates": ["gap_quality_gate"],
            }
        ],
    }
    path = experiment_dir / "feature_regime_experiment_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_multi_symbol_feature_regime_analyzer_aggregates_expected_fields(tmp_path: Path) -> None:
    root = tmp_path / "feature_regime_experiments"
    btc = _write_summary(
        root,
        experiment_id="btc_exp",
        symbol="BTCUSDT",
        score=-2.003547,
        edge=0.018072,
        profit_factor=1.009218,
        walk_forward_profit_factor=0.972727,
        failed_gates=["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
        real_feature_diagnostics_used=True,
        row_count=50453,
        regime_features_attached=True,
    )
    eth = _write_summary(
        root,
        experiment_id="eth_exp",
        symbol="ETHUSDT",
        score=-2.965675,
        edge=0.032728,
        profit_factor=0.0,
        walk_forward_profit_factor=0.972161,
        failed_gates=["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
        real_feature_diagnostics_used=False,
        row_count=0,
        regime_features_attached=False,
    )
    sol = _write_summary(
        root,
        experiment_id="sol_exp",
        symbol="SOLUSDT",
        score=-3.388438,
        edge=-0.003011,
        profit_factor=1.071715,
        walk_forward_profit_factor=0.982248,
        failed_gates=["baseline_edge_gate", "collapse_gate", "walk_forward_gate"],
        real_feature_diagnostics_used=False,
        row_count=0,
        regime_features_attached=False,
    )

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze([btc, eth, sol])

    assert payload["best_symbol"] == "BTCUSDT"
    assert payload["best_candidate_score"] == -2.003547
    assert payload["candidate_count"] == 3
    assert payload["accepted_candidate_count"] == 0
    assert payload["rejected_candidate_count"] == 3
    assert payload["gate_failure_counts"]["collapse_gate"] == 3
    assert payload["gate_failure_counts"]["walk_forward_gate"] == 3
    assert payload["gate_failure_counts"]["profit_aware_gate"] == 2
    assert payload["top_failed_gate"] == "collapse_gate"
    assert payload["all_feature_version_fv2"] is True
    assert payload["all_gap_training_safe"] is True
    assert payload["all_real_feature_diagnostics_used"] is False
    assert payload["any_accepted_candidate"] is False
    assert payload["any_positive_baseline_edge"] is True
    assert payload["all_positive_baseline_edge"] is False
    assert payload["configs_ranked"][0]["baseline_edge"] == 0.018072
    assert payload["configs_ranked"][0]["baseline_edge_status"] == "STRONG_EDGE"
    assert payload["configs_ranked"][0]["collapse_severity"] == "WATCH"
    assert payload["symbols_missing_real_diagnostics"] == ["ETHUSDT", "SOLUSDT"]
    assert payload["symbols_missing_regime_features"] == ["ETHUSDT", "SOLUSDT"]
    assert payload["collapse_failed_count"] == 3
    assert payload["walk_forward_failed_count"] == 3
    assert payload["profit_aware_failed_count"] == 2
    assert json.dumps(payload)
