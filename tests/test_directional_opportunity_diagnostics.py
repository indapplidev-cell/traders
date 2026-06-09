from app.diagnostics.directional_opportunity_diagnostics import DirectionalOpportunityDiagnostics


def test_directional_opportunity_diagnostics_marks_long_only_segment() -> None:
    diagnostics = DirectionalOpportunityDiagnostics()
    fold_report = diagnostics.build_fold_report(
        fold=_fold(),
        validation_long=_summary(signal_count=10, profit_factor=1.2, total_r=3.0),
        validation_short=_summary(signal_count=10, profit_factor=0.8, total_r=-2.0),
        test_long=_summary(signal_count=12, profit_factor=1.4, total_r=4.0),
        test_short=_summary(signal_count=12, profit_factor=0.7, total_r=-3.0),
    )
    report = diagnostics.build_report(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv1",
        label_version="lv1",
        folds=[fold_report],
    )

    assert "long_only_market_segment" in fold_report["warnings"]
    assert report["summary"]["short_opportunities_exist"] is False
    assert report["summary"]["better_side"] == "LONG"


def _fold() -> dict[str, object]:
    return {
        "fold_index": 1,
        "train_start": "2025-01-01T00:00:00+00:00",
        "train_end": "2025-02-01T00:00:00+00:00",
        "validation_start": "2025-02-01T00:00:00+00:00",
        "validation_end": "2025-02-11T00:00:00+00:00",
        "test_start": "2025-02-11T00:00:00+00:00",
        "test_end": "2025-02-21T00:00:00+00:00",
    }


def _summary(signal_count: int, profit_factor: float, total_r: float) -> dict[str, object]:
    return {
        "signal_count": signal_count,
        "profit_factor": profit_factor,
        "total_r": total_r,
        "win_count": 5,
        "loss_count": 3,
        "neither_count": 2,
        "gross_profit_r": 5.0,
        "gross_loss_r": 2.0,
        "expectancy_r": total_r / signal_count if signal_count else None,
        "win_rate": 0.5,
    }
