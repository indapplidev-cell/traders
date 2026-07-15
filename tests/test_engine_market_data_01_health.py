from app.engine_market_data.exchange_time_sync import ExchangeTimeSync
from app.engine_market_data.market_data_health import MarketDataHealth, MarketDataHealthStatus


def test_all_required_health_states_exist() -> None:
    assert {state.value for state in MarketDataHealthStatus} == {
        "OK", "DEGRADED", "STALE", "DISCONNECTED", "RECOVERING", "ERROR",
    }


def test_health_transitions_keep_reasons() -> None:
    health = MarketDataHealth()
    health.stale()
    assert health.status == MarketDataHealthStatus.STALE
    assert "stale latest candle" in health.reasons
    health.ok()
    assert health.reasons == []


def test_exchange_time_drift_degrades_health_and_adjusts_now() -> None:
    class Rest:
        def fetch_server_time_ms(self) -> int: return 2_500

    times = iter([1_000, 1_000, 1_100])
    health = MarketDataHealth()
    sync = ExchangeTimeSync(Rest(), health=health, max_drift_ms=100, clock_ms=lambda: next(times))
    result = sync.sync()
    assert result.drift_ms == 1_500
    assert health.status == "DEGRADED"
    assert sync.now_ms_exchange_adjusted() == 2_600
