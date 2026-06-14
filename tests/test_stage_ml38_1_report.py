from pathlib import Path


def test_stage_ml38_1_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml38_1_fv3_multisymbol_diagnostics_propagation_report.md")
    text = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML38.1",
        "fv3_candle_ta_context",
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "multi-symbol propagation",
        "diagnostics propagation",
        "silent fallback",
        "pytest results",
        "CLI results",
        "fresh archive",
        "candle_ta_context_features_attached",
        "real_feature_diagnostics_used",
        "regime_features_attached",
        "Can proceed to ML38.2 tuning",
        "Can proceed to ML39 Schwager evaluation hardening",
        "no traders-core",
        "no live",
        "no orders",
        "no auto activation",
    ):
        assert expected in text
