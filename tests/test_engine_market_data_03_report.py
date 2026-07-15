import json

from app.engine_market_data.historical_backfill_report import BackfillTaskReport, HistoricalBackfillReport


def test_report_aggregates_totals_and_serializes():
    item = BackfillTaskReport("BTCUSDT", "1m", 2, 0, 60_000, 2,
                              existing_before=1, missing_before=1, rest_calls=1,
                              downloaded_candles=1, accepted_candles=1,
                              upserted_candles=1, existing_after=2, status="SUCCESS")
    report = HistoricalBackfillReport(symbols=["BTCUSDT"], timeframes=["1m"], task_reports=[item]).finish()
    payload = json.loads(report.to_json())
    assert payload["tasks_success"] == 1
    assert payload["expected_candles_total"] == 2
    assert payload["rest_calls_total"] == 1 and not payload["future_bars_used"]

