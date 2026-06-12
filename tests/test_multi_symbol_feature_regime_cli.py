import json
import os
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli


def _write_summary(
    root: Path,
    *,
    experiment_id: str,
    symbol: str,
    score: float,
    real_feature_diagnostics_used: bool,
    row_count: int,
    regime_features_attached: bool,
    failed_gates: list[str],
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
                "accuracy_edge": 0.01,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 1.0,
                "profit_total_r": -10.0,
                "walk_forward_profit_factor": 0.97,
                "walk_forward_global_total_r": -20.0,
                "failed_gates": failed_gates,
                "passed_gates": ["gap_quality_gate"],
                "warnings": [],
            }
        ],
    }
    summary_path = experiment_dir / "feature_regime_experiment_summary.json"
    summary_path.write_text(json.dumps(payload), encoding="utf-8")
    return summary_path


def test_multi_symbol_feature_regime_cli_latest_per_symbol_and_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "reports" / "feature_regime_experiments"
    old_btc = _write_summary(
        root,
        experiment_id="btc_old",
        symbol="BTCUSDT",
        score=-5.0,
        real_feature_diagnostics_used=True,
        row_count=10,
        regime_features_attached=True,
        failed_gates=["collapse_gate"],
    )
    new_btc = _write_summary(
        root,
        experiment_id="btc_new",
        symbol="BTCUSDT",
        score=-2.003547,
        real_feature_diagnostics_used=True,
        row_count=50453,
        regime_features_attached=True,
        failed_gates=["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
    )
    eth = _write_summary(
        root,
        experiment_id="eth_new",
        symbol="ETHUSDT",
        score=-2.965675,
        real_feature_diagnostics_used=False,
        row_count=0,
        regime_features_attached=False,
        failed_gates=["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
    )
    sol = _write_summary(
        root,
        experiment_id="sol_new",
        symbol="SOLUSDT",
        score=-3.388438,
        real_feature_diagnostics_used=False,
        row_count=0,
        regime_features_attached=False,
        failed_gates=["baseline_edge_gate", "collapse_gate", "walk_forward_gate"],
    )
    os.utime(old_btc, (1_700_000_000, 1_700_000_000))
    os.utime(new_btc, (1_800_000_000, 1_800_000_000))
    os.utime(eth, (1_800_000_100, 1_800_000_100))
    os.utime(sol, (1_800_000_200, 1_800_000_200))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "multi-symbol-feature-regime-analyze",
            "--experiments-root",
            str(root),
            "--symbols",
            "BTCUSDT,ETHUSDT,SOLUSDT",
            "--latest-per-symbol",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["best_symbol"] == "BTCUSDT"
    assert payload["best_candidate_score"] == -2.003547
    assert payload["all_feature_version_fv2"] is True
    assert payload["all_gap_training_safe"] is True
    assert payload["all_real_feature_diagnostics_used"] is False
    assert payload["symbols_missing_real_diagnostics"] == ["ETHUSDT", "SOLUSDT"]
    assert payload["symbols_missing_regime_features"] == ["ETHUSDT", "SOLUSDT"]
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
    assert payload["orders_enabled"] is False
    assert payload["traders_core_connected"] is False
    assert Path(payload["analysis_json_path"]).exists()
    assert Path(payload["analysis_markdown_path"]).exists()


def test_multi_symbol_feature_regime_cli_no_export_does_not_write_reports(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "reports" / "feature_regime_experiments"
    _write_summary(
        root,
        experiment_id="btc_only",
        symbol="BTCUSDT",
        score=-2.003547,
        real_feature_diagnostics_used=True,
        row_count=50453,
        regime_features_attached=True,
        failed_gates=["collapse_gate", "profit_aware_gate", "walk_forward_gate"],
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "multi-symbol-feature-regime-analyze",
            "--experiments-root",
            str(root),
            "--symbols",
            "BTCUSDT",
            "--latest-per-symbol",
            "--no-export-report",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["analysis_json_path"] is None
    assert payload["analysis_markdown_path"] is None
    assert not (tmp_path / "reports" / "multi_symbol_feature_regime_analysis.json").exists()
    assert not (tmp_path / "reports" / "multi_symbol_feature_regime_analysis.md").exists()

