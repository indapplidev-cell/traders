from pathlib import Path


def test_stage_ml38_10_35_report_exists_and_documents_scope():
    path = Path("reports/stage_ml38_10_35_metric_relaxation_probe_report.md")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "ML38.10.35" in text
    assert "metric-relaxation diagnostic probe" in text
    assert "No runtime" in text
    assert "No fast-debug" in text
    assert "No quick-quality" in text
    assert "research-only" in text
