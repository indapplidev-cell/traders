from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.freshness_gate import FreshnessGate


DELAYS = {"15m": 21, "1h": 61, "4h": 91, "1d": 121}
TIMEFRAMES = ("15m", "1h", "4h", "1d")


class AuditRepo:
    def __init__(self, boundary, observed_at, missing_forever=False):
        self.boundary = boundary
        self.observed_at = observed_at
        self.missing_forever = missing_forever

    def list_for(self, symbols, timeframes):
        rows = []
        for timeframe in timeframes:
            duration = timeframe_to_milliseconds(timeframe)
            required = self.boundary // duration * duration
            closes_now = self.boundary % duration == 0
            available_at = datetime.fromtimestamp(self.boundary / 1000, tz=timezone.utc)
            if closes_now:
                available_at += timedelta(seconds=DELAYS[timeframe])
            unavailable = self.observed_at < available_at
            if self.missing_forever and timeframe == "1h" and closes_now:
                unavailable = True
            close = required - duration if unavailable else required
            rows.append(SimpleNamespace(
                timeframe=timeframe, status="OK", last_stored_close_boundary_ms=close,
                last_stored_open_time_ms=close - duration,
            ))
        return rows


def simulate(*, one_timeout=False):
    start = datetime(2026, 7, 17, tzinfo=timezone.utc)
    completed = recovered = timeouts = snapshots_before_ready = 0
    identities = set()
    results = set()
    timeout_identity = ("BTCUSDT", int((start + timedelta(hours=1)).timestamp() * 1000))
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for quarter in range(1, 97):
            boundary_dt = start + timedelta(minutes=15 * quarter)
            boundary = int(boundary_dt.timestamp() * 1000)
            identity = (symbol, boundary)
            assert identity not in identities
            identities.add(identity)
            observed = boundary_dt + timedelta(seconds=DELAYS["15m"])
            deadline = boundary_dt + timedelta(seconds=180)
            missing_forever = one_timeout and identity == timeout_identity
            waited = False
            while True:
                decision = FreshnessGate(
                    AuditRepo(boundary, observed, missing_forever), TIMEFRAMES,
                    clock=lambda observed=observed: observed,
                ).check(symbol, boundary, deadline_at=deadline, now=observed)
                if decision.allowed:
                    completed += 1
                    recovered += int(waited)
                    assert identity not in results
                    results.add(identity)
                    break
                if decision.reason_code == "FRESHNESS_TIMEOUT":
                    timeouts += 1
                    break
                assert decision.status == "WAITING_FOR_REQUIRED_BOUNDARY"
                waited = True
                snapshots_before_ready += 0
                observed = min(observed + timedelta(seconds=5), deadline)
    return {
        "logical": len(identities), "completed": completed, "recovered": recovered,
        "timeouts": timeouts, "duplicates": len(results) - len(set(results)),
        "snapshot_before_ready": snapshots_before_ready,
    }


def test_24h_audit_all_boundaries_recover():
    assert simulate() == {
        "logical": 288, "completed": 288, "recovered": 72,
        "timeouts": 0, "duplicates": 0, "snapshot_before_ready": 0,
    }


def test_24h_one_missing_hour_times_out():
    value = simulate(one_timeout=True)
    assert value["logical"] == 288
    assert value["completed"] == 287
    assert value["timeouts"] == 1
    assert value["duplicates"] == 0
