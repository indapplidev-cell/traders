from pathlib import Path


def test_stage_ml36_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml36_collapse_regime_walkforward_report.md")
    payload = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML36",
        "collapse_gate",
        "walk-forward",
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "regime label builder",
        "real diagnostics",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML37",
    ):
        assert expected in payload
