from pathlib import Path


def test_stage_ml38_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml38_candle_ta_context_feature_layer_report.md")
    text = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML38",
        "fv3_candle_ta_context",
        "Nison",
        "Altunina",
        "candle morphology",
        "candle patterns",
        "technical context",
        "lookahead",
        "NaN/inf",
        "files changed",
        "tests added",
        "pytest results",
        "CLI results",
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
        "ML39",
    ):
        assert expected in text
