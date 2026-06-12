from pathlib import Path


def test_stage_ml36_1_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml36_1_runtime_regime_label_quality_gap_report.md")
    text = path.read_text(encoding="utf-8")

    assert "BTC/ETH/SOL" in text
    assert "regime_runtime_labels_not_built" in text
    assert "model_quality_validation" in text
    assert "candidate_status=UNKNOWN" in text
    assert "gap gate" in text
    assert "diagnostics propagation" in text
    assert "traders-core integration: no" in text
    assert "live trading: no" in text
