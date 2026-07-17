from datetime import datetime, timedelta, timezone

from app.engine_observation.observation_models import ResultRecord, RunRecord

UTC = timezone.utc
START = datetime(2026, 7, 16, tzinfo=UTC)


def run(index=0, symbol="BTCUSDT", **changes):
    boundary = START + timedelta(minutes=15 * index)
    values = dict(run_id=f"run-{symbol}-{index}", symbol=symbol, primary_timeframe="15m",
        closed_until_ms=int(boundary.timestamp() * 1000), closed_until_utc=boundary,
        status="COMPLETED", started_at=boundary + timedelta(seconds=2),
        finished_at=boundary + timedelta(seconds=3), duration_ms=1000,
        trigger_source="postgres_closed_candle", daemon_instance_id="daemon-1",
        market_data_freshness_status="OK", analysis_status="ANALYZED", setup_status="NO_SETUP",
        strategy_status="NO_DECISION", risk_status="NO_DECISION", paper_status="NO_PLAN",
        final_result="NO_PLAN")
    values.update(changes)
    return RunRecord(**values)


def result(value=None, **changes):
    run_value = value or run()
    values = dict(run_id=run_value.run_id, symbol=run_value.symbol, primary_timeframe="15m",
                  closed_until_ms=run_value.closed_until_ms, module_reasons_json={"paper": ["NO_VALID_PLAN"]})
    values.update(changes)
    return ResultRecord(**values)
