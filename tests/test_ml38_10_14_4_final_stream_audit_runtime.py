from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.evaluation.signal_gate_evaluator import SignalGateEvaluator
from app.experiments.feature_regime_experiment_runner import FeatureRegimeCandidateResult
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.experiments.multi_symbol_feature_regime_reporter import MultiSymbolFeatureRegimeReporter


def _runtime_prediction(
    *,
    original_label: str,
    actual: str,
    blocked: bool,
    reason: str | None = None,
    quality: float = 0.80,
    stop: float = 0.20,
) -> dict[str, object]:
    return {
        "predicted_label": "FLAT" if blocked else original_label,
        "entry_path_original_predicted_label": original_label,
        "entry_path_filtered_predicted_label": "FLAT" if blocked else original_label,
        "actual_label": actual,
        "prob_up": 0.80 if original_label == "UP" else 0.10,
        "prob_down": 0.80 if original_label == "DOWN" else 0.10,
        "prob_flat": 0.10,
        "confidence": 0.80,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [{"high": 101.2, "low": 99.2}],
        "future_move_atr": 1.0,
        "entry_path_filter_enabled": True,
        "entry_path_filter_blocked": blocked,
        "entry_path_filter_block_reason": reason,
        "entry_path_filter_threshold": 0.70,
        "entry_path_filter_stop_threshold": 0.45,
        "entry_path_quality_score": quality,
        "stop_pressure_risk_score": stop,
    }


def test_ml38_10_14_4_signal_gate_raw_stream_uses_original_label_after_runtime_mutation() -> None:
    evaluator = SignalGateEvaluator()
    rows = [
        _runtime_prediction(original_label="UP", actual="UP", blocked=False),
        _runtime_prediction(
            original_label="UP",
            actual="FLAT",
            blocked=True,
            reason="high_stop_pressure",
            stop=0.90,
        ),
    ]

    raw = evaluator.select_signals(rows, "max_prob", 0.50, apply_entry_path_filter=False)
    filtered = evaluator.select_signals(rows, "max_prob", 0.50, apply_entry_path_filter=True)

    assert raw["signal_count"] == 2
    assert filtered["signal_count"] == 1
    assert filtered["skipped_entry_path_filter_count"] == 1
    assert raw["signal_rows"][1]["signal_direction"] == "LONG"
    assert raw["signal_rows"][1]["signal_gate_predicted_label"] == "UP"


def test_ml38_10_14_4_profit_audit_counts_blocked_final_signals_after_runtime_mutation() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    rows = [
        _runtime_prediction(original_label="UP", actual="UP", blocked=False),
        _runtime_prediction(
            original_label="UP",
            actual="FLAT",
            blocked=True,
            reason="high_stop_pressure",
            stop=0.90,
        ),
        _runtime_prediction(
            original_label="DOWN",
            actual="UP",
            blocked=True,
            reason="low_entry_quality",
            quality=0.20,
        ),
    ]

    payload = evaluator.evaluate_single_gate(
        predictions=rows,
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.0,
    )
    summary = payload["summary"]["entry_path_prediction_filter_summary"]
    stop_audit = payload["summary"]["stop_pressure_effectiveness_audit"]

    assert summary["audit_stream"] == "final_profit_aware_gate_signal_stream"
    assert summary["original_final_signal_count"] == 3
    assert summary["filtered_final_signal_count"] == 1
    assert summary["blocked_final_signal_count"] == 2
    assert summary["stream_consistency_ok"] is True
    assert stop_audit["blocked_by_high_stop_pressure_count"] == 1
    assert stop_audit["stream_consistency_ok"] is True


def test_ml38_10_14_4_feature_regime_candidate_serializes_entry_path_audit() -> None:
    candidate = FeatureRegimeCandidateResult(
        candidate_id="lv22",
        config_id="lv22",
        label_config={"config_id": "lv22"},
        status="REJECTED",
        quality_status="QUALITY_REJECTED",
        candidate_status="REJECTED",
        raw_candidate_status="CANDIDATE_REJECTED",
        score=1.0,
        entry_path_quality_filter_enabled=True,
        entry_path_quality_min_threshold=0.70,
        stop_pressure_max_risk_score=0.45,
        entry_path_prediction_filter_summary={
            "original_final_signal_count": 10,
            "filtered_final_signal_count": 7,
            "blocked_final_signal_count": 3,
            "stream_consistency_ok": True,
        },
        stop_pressure_effectiveness_audit={"status": "STOP_PRESSURE_REMOVED_FALSE_SIGNALS"},
    )

    payload = candidate.to_dict()

    assert payload["entry_path_quality_filter_enabled"] is True
    assert payload["entry_path_quality_min_threshold"] == 0.70
    assert payload["stop_pressure_max_risk_score"] == 0.45
    assert payload["entry_path_prediction_filter_summary"]["blocked_final_signal_count"] == 3
    assert payload["stop_pressure_effectiveness_audit"]["status"] == "STOP_PRESSURE_REMOVED_FALSE_SIGNALS"


def test_ml38_10_14_4_configs_ranked_receives_entry_path_audit_from_candidate_results() -> None:
    summary = {
        "symbol": "SOLUSDT",
        "experiment_id": "exp1",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv22",
        "feature_version_used": "fv4_book_setup_context",
        "gap_severity_for_training": "NONE",
        "gap_training_safe": True,
        "candidate_results": [
            {
                "config_id": "lv22",
                "candidate_status": "REJECTED",
                "score": 1.5,
                "failed_gates": ["profit_aware_gate"],
                "passed_gates": [],
                "entry_path_quality_filter_enabled": True,
                "entry_path_quality_min_threshold": 0.70,
                "stop_pressure_max_risk_score": 0.45,
                "entry_path_prediction_filter_summary": {
                    "diagnostic_version": "ml38.10.14.4",
                    "audit_stream": "final_profit_aware_gate_signal_stream",
                    "original_final_signal_count": 10,
                    "filtered_final_signal_count": 7,
                    "blocked_final_signal_count": 3,
                    "stream_consistency_ok": True,
                    "stop_pressure_effectiveness_audit": {
                        "diagnostic_version": "ml38.10.14.4",
                        "status": "STOP_PRESSURE_REMOVED_FALSE_SIGNALS",
                    },
                },
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv22",
                "candidate_status": "REJECTED",
                "score": 1.5,
                "failed_gates": ["profit_aware_gate"],
                "passed_gates": [],
            }
        ],
    }

    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(summary)

    assert result["configs_ranked"][0]["entry_path_final_signal_original_count"] == 10
    assert result["configs_ranked"][0]["entry_path_final_signal_filtered_count"] == 7
    assert result["configs_ranked"][0]["entry_path_final_signal_blocked_count"] == 3
    assert result["configs_ranked"][0]["entry_path_stream_consistency_ok"] is True


def test_ml38_10_14_4_reporter_has_single_entry_path_section() -> None:
    reporter = MultiSymbolFeatureRegimeReporter()
    payload = {
        "symbols": ["SOLUSDT"],
        "experiment_count": 1,
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "symbol_results": [
            {
                "symbol": "SOLUSDT",
                "best_candidate_config_id": "lv22",
                "entry_path_quality_filter_enabled": True,
                "entry_path_quality_min_threshold": 0.70,
                "stop_pressure_max_risk_score": 0.45,
                "entry_path_final_signal_original_count": 10,
                "entry_path_final_signal_filtered_count": 7,
                "entry_path_final_signal_blocked_count": 3,
                "entry_path_stream_consistency_ok": True,
                "stop_pressure_effectiveness_audit": {
                    "status": "STOP_PRESSURE_REMOVED_FALSE_SIGNALS",
                },
            }
        ],
    }

    markdown = reporter._markdown(payload)

    assert markdown.count("## Entry-Path / Stop-Pressure Audit") == 1
    assert "| `SOLUSDT` | `lv22` | `True` | `0.7` | `0.45` | `10` | `7` | `3` | `True` | `STOP_PRESSURE_REMOVED_FALSE_SIGNALS` |" in markdown
