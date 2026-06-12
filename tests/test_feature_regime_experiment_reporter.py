import json
from pathlib import Path

from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter


def test_feature_regime_experiment_reporter_writes_summary_and_candidate_files(tmp_path: Path) -> None:
    reporter = FeatureRegimeExperimentReporter()
    result_payload = {
        "experiment_id": "fr_test",
        "symbol": "BTCUSDT",
        "interval": "15m",
        "start_date": "2025-01-01",
        "end_date": "2025-01-02",
        "status": "ok",
        "experiment_status": "SAMPLE_COMPLETED",
        "config_count": 2,
        "candidate_count": 2,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 2,
        "best_candidate_id": "sample_cfg_1",
        "best_candidate_config_id": "cfg_1",
        "best_candidate_score": -6.1,
        "feature_quality_summary": {"weak_signal_detected": True},
        "feature_group_quality_summary": {"groups": []},
        "regime_feature_summary": {"regime_data_available": True},
        "feature_leakage_summary": {"leakage_risk_detected": False},
        "regime_experiment_plan_summary": {"ready_for_real_regime_training": True},
        "candidate_results": [],
        "ranking": [],
        "recommendations": ["keep research only"],
        "regime_training_applied": False,
    }
    candidate_payload = {
        "candidate_id": "sample_cfg_1",
        "config_id": "cfg_1",
        "status": "COMPLETED",
        "candidate_status": "CANDIDATE_REJECTED",
        "quality_status": "QUALITY_REJECTED",
        "score": -6.1,
        "failed_gates": ["collapse_gate"],
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "orders_enabled": False,
        "traders_core_connected": False,
    }

    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"
    diag_json = tmp_path / "diagnostics" / "feature_quality.json"
    candidate_json = tmp_path / "candidate.json"
    candidate_md = tmp_path / "candidate.md"

    reporter.write_summary_json(result_payload, summary_json)
    reporter.write_summary_markdown(result_payload, summary_md)
    reporter.write_diagnostics_json({"ok": True}, diag_json)
    reporter.write_candidate_json(candidate_payload, candidate_json)
    reporter.write_candidate_markdown(candidate_payload, candidate_md)

    assert json.loads(summary_json.read_text(encoding="utf-8"))["experiment_id"] == "fr_test"
    assert "## Safety" in summary_md.read_text(encoding="utf-8")
    assert json.loads(diag_json.read_text(encoding="utf-8"))["ok"] is True
    assert json.loads(candidate_json.read_text(encoding="utf-8"))["candidate_id"] == "sample_cfg_1"
    assert "## Safety" in candidate_md.read_text(encoding="utf-8")
