from app.diagnostics.baseline_edge_diagnostics import BaselineEdgeDiagnostics


def test_baseline_edge_diagnostics_detects_negative_edge() -> None:
    result = BaselineEdgeDiagnostics().evaluate(
        accuracy=0.33,
        baseline_accuracy=0.36,
        symbol="SOLUSDT",
        config_id="cfg",
    )

    assert result.baseline_edge < 0
    assert result.baseline_edge_status == "NEGATIVE_EDGE"
    assert result.baseline_edge_gate_failed is True


def test_baseline_edge_diagnostics_detects_positive_edge() -> None:
    result = BaselineEdgeDiagnostics().evaluate(
        accuracy=0.39,
        baseline_accuracy=0.36,
        symbol="SOLUSDT",
        config_id="cfg",
    )

    assert result.baseline_edge > 0
    assert result.baseline_edge_status == "STRONG_EDGE"
    assert result.baseline_edge_gate_failed is False
