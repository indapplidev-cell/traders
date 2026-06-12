from pathlib import Path


def test_stage_ml35_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml35_real_feature_regime_multisymbol_report.md")
    payload = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML35",
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "fv2",
        "gap training safe",
        "real feature diagnostics",
        "multi-symbol",
        "collapse",
        "walk-forward",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML36",
    ):
        assert expected in payload

