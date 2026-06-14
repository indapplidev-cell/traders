from pathlib import Path


def test_stage_ml38_2_report_contains_required_topics() -> None:
    path = Path("reports/stage_ml38_2_fv3_label_threshold_collapse_tuning_report.md")
    text = path.read_text(encoding="utf-8")

    for expected in (
        "Stage ML38.2",
        "FV3 Label, Threshold and Collapse Tuning",
        "fv3_candle_ta_context",
        "flat bias",
        "down blindness",
        "collapse summary",
        "best_config_by_symbol",
        "best_global_config",
        "configs evaluated",
        "fresh grid script path",
        "fresh archive path",
        "Can proceed to ML38.3",
        "Can proceed to ML39",
        "traders-core integration: no",
        "live trading: no",
        "orders/trades: no",
        "model auto activation: no",
    ):
        assert expected in text
