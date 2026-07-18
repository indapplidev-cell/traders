from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.freshness_gate import FreshnessClassification, FreshnessGate


HOUR = 3_600_000
BOUNDARY = 1_768_176_000_000  # UTC hour boundary
NOW = datetime.fromtimestamp((BOUNDARY + 30_000) / 1000, tz=timezone.utc)


class Repo:
    def __init__(self, missing=(), status=None, latest_override=None):
        self.missing = set(missing)
        self.status = status or {}
        self.latest_override = latest_override or {}

    def list_for(self, symbols, timeframes):
        rows = []
        for timeframe in timeframes:
            duration = timeframe_to_milliseconds(timeframe)
            required = BOUNDARY // duration * duration
            close = self.latest_override.get(timeframe, required)
            if timeframe in self.missing:
                close = required - duration
            rows.append(SimpleNamespace(
                timeframe=timeframe, status=self.status.get(timeframe, "OK"),
                last_stored_open_time_ms=close - duration,
                last_stored_close_boundary_ms=close,
            ))
        return rows


def decision(repo, timeframes=("15m", "1h"), *, now=NOW, deadline=None):
    return FreshnessGate(repo, timeframes, clock=lambda: now).check(
        "BTCUSDT", BOUNDARY, deadline_at=deadline or NOW + timedelta(seconds=150),
    )


def test_ready_contract_and_availability_payload():
    value = decision(Repo())
    assert value.allowed and value.classification == FreshnessClassification.READY
    assert all(item.required_boundary_available for item in value.availability)
    assert value.payload()["timeframes"][0]["health_state"] == "OK"


def test_ordinary_quarter_hour_uses_previous_closed_hour_and_is_ready():
    quarter = BOUNDARY + 15 * 60_000

    class QuarterRepo:
        def list_for(self, symbols, timeframes):
            return [
                SimpleNamespace(timeframe="15m", status="OK",
                                last_stored_open_time_ms=quarter - 15 * 60_000,
                                last_stored_close_boundary_ms=quarter),
                SimpleNamespace(timeframe="1h", status="OK",
                                last_stored_open_time_ms=BOUNDARY - HOUR,
                                last_stored_close_boundary_ms=BOUNDARY),
            ]

    checked_at = NOW + timedelta(minutes=15)
    value = FreshnessGate(QuarterRepo(), ("15m", "1h"), clock=lambda: checked_at).check(
        "BTCUSDT", quarter, deadline_at=checked_at + timedelta(seconds=180))
    assert value.allowed and value.status == "READY"


def test_health_ok_without_boundary_is_transient_wait():
    value = decision(Repo(missing=("1h",)))
    assert not value.allowed
    assert value.classification == FreshnessClassification.TRANSIENT_NOT_READY
    assert value.status == "WAITING_FOR_REQUIRED_BOUNDARY"
    assert value.reason_code == "1h:BOUNDARY_NOT_READY"
    assert value.missing_timeframes == ("1h",)


@pytest.mark.parametrize(
    ("missing", "reason"),
    [
        (("1h",), "1h:BOUNDARY_NOT_READY"),
        (("1h", "4h"), "MULTIPLE_REQUIRED_BOUNDARIES_NOT_READY"),
        (("1h", "4h", "1d"), "MULTIPLE_REQUIRED_BOUNDARIES_NOT_READY"),
    ],
)
def test_hour_4h_and_daily_missing_boundaries_wait(missing, reason):
    value = decision(Repo(missing=missing), ("15m", "1h", "4h", "1d"))
    assert value.classification == "TRANSIENT_NOT_READY"
    assert value.reason_code == reason


def test_deadline_changes_missing_boundary_to_distinct_timeout():
    value = decision(Repo(missing=("1h",)), deadline=NOW)
    assert value.classification == "TERMINAL_NOT_READY"
    assert value.reason_code == "FRESHNESS_TIMEOUT"


def test_persistent_gap_is_terminal_before_deadline():
    value = decision(Repo(missing=("1h",), status={"1h": "GAP_DETECTED"}))
    assert value.classification == "TERMINAL_NOT_READY"
    assert value.reason_code == "PERSISTENT_GAP"


def test_future_state_boundary_is_terminal_safety_failure():
    value = decision(Repo(latest_override={"1h": BOUNDARY + HOUR}))
    assert value.reason_code == "FUTURE_OR_UNCLOSED_DATA"


def test_stale_health_never_proves_missing_boundary_available():
    value = FreshnessGate(
        Repo(missing=("1h",), status={"1h": "STALE"}), ("15m", "1h"),
        allow_stale_higher_timeframes=True, clock=lambda: NOW,
    ).check("BTCUSDT", BOUNDARY, deadline_at=NOW + timedelta(seconds=150))
    assert value.classification == "TRANSIENT_NOT_READY"
    assert not value.availability[1].required_boundary_available


def test_invalid_boundary_is_terminal_and_naive_clock_rejected():
    gate = FreshnessGate(Repo(), ("15m",), clock=lambda: NOW)
    assert gate.check("BTCUSDT", 0).reason_code == "INVALID_BOUNDARY"
    with pytest.raises(ValueError, match="timezone-aware"):
        gate.check("BTCUSDT", BOUNDARY, now=datetime(2026, 1, 1))
