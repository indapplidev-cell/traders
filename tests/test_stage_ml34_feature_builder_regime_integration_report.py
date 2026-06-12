from pathlib import Path


def test_stage_ml34_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml34_feature_builder_regime_integration_report.md")
    payload = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML34",
        "BTC/ETH/SOL",
        "trailing incomplete",
        "gap_quality",
        "real feature diagnostics",
        "additive features",
        "fv2",
        "regime features",
        "regime-specific training",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML35",
    ):
        assert expected in payload
