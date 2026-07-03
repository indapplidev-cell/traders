from pathlib import Path


def test_stage_ml38_10_34_report_exists_and_documents_scope():
    path = Path("reports/stage_ml38_10_34_lv35_metric_overlap_diagnostics_report.md")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "ML38.10.34" in text
    assert "metric-overlap" in text or "metric overlap" in text
    assert "conditional_regime_metric_overlap_board" in text
    assert "No runtime execution" in text
    assert "No live trading" in text
