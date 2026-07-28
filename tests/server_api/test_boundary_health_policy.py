from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.engine_market_data.db.base import Base
from app.engine_market_data.db.candle_tables import Candle15m
from app.engine_orchestrator.orchestrator_models import OnlinePipelineRun
from app.server_api.health_policy import evaluate_boundary_health
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter


BOUNDARY = datetime(2026, 7, 27, 22, 0, tzinfo=timezone.utc)
BOUNDARY_MS = int(BOUNDARY.timestamp() * 1000)


def run(
    *,
    timeframe="1h",
    available=False,
    health="OK",
    run_status="WAITING_FOR_REQUIRED_BOUNDARY",
    classification="WAITING_RETRYABLE",
    payload_status="WAITING_FOR_REQUIRED_BOUNDARY",
    blocker_kind="BOUNDARY_NOT_READY",
    blocker_code="BOUNDARY_NOT_READY",
    error_code=None,
):
    return SimpleNamespace(
        status=run_status,
        error_code=error_code,
        market_data_freshness_status=payload_status,
        last_freshness_payload={
            "classification": classification,
            "status": payload_status,
            "timeframes": [{
                "timeframe": timeframe,
                "health_state": health,
                "required_boundary_close_time": BOUNDARY_MS,
                "required_boundary_available": available,
                "reason_code": None if available else f"{timeframe}:BOUNDARY_NOT_READY",
            }],
            "blocking_reasons": [] if available else [{
                "timeframe": timeframe,
                "kind": blocker_kind,
                "code": blocker_code,
                "health_status": health,
                "required_boundary_ms": BOUNDARY_MS,
                "retryable": True,
            }],
        },
    )


@pytest.mark.parametrize("offset", [0, 51, 60])
def test_original_1h_failure_and_inclusive_grace_edge_are_non_blocking(offset):
    decision = evaluate_boundary_health(run(), candle_available=True, now=BOUNDARY + timedelta(seconds=offset))
    assert (
        decision.status,
        decision.timing_state,
        decision.reason_code,
        decision.operational,
        decision.ready,
        decision.acceptance_blocking,
    ) == ("OK", "WITHIN_GRACE", "BOUNDARY_WITHIN_GRACE", True, True, False)


def test_first_supported_millisecond_after_grace_is_blocking():
    decision = evaluate_boundary_health(
        run(), candle_available=True, now=BOUNDARY + timedelta(seconds=60, milliseconds=1)
    )
    assert (decision.status, decision.timing_state, decision.acceptance_blocking) == (
        "DEGRADED", "DEADLINE_EXPIRED", True
    )


@pytest.mark.parametrize(
    ("health", "kind", "code"),
    [
        ("GAP_DETECTED", "HEALTH_STATUS_NOT_OK", "STATUS_GAP_DETECTED"),
        ("ERROR", "HEALTH_STATUS_NOT_OK", "STATUS_ERROR"),
        ("STALE", "HEALTH_STATUS_NOT_OK", "NO_PROGRESS"),
    ],
)
def test_real_gap_active_error_and_no_progress_remain_blocking(health, kind, code):
    decision = evaluate_boundary_health(
        run(health=health, blocker_kind=kind, blocker_code=code),
        candle_available=True,
        now=BOUNDARY + timedelta(seconds=5),
    )
    assert decision.status == "DEGRADED"
    assert decision.acceptance_blocking is True


def test_terminal_deadline_remains_blocking():
    decision = evaluate_boundary_health(
        run(classification="TERMINAL_NOT_READY", payload_status="FRESHNESS_DEADLINE_EXCEEDED"),
        candle_available=True,
        now=BOUNDARY + timedelta(seconds=5),
    )
    assert (decision.status, decision.timing_state) == ("DEGRADED", "DEADLINE_EXPIRED")


def test_current_synchronized_state_is_ok():
    decision = evaluate_boundary_health(
        run(available=True, run_status="COMPLETED", classification="READY", payload_status="READY"),
        candle_available=True,
        now=BOUNDARY + timedelta(seconds=65),
    )
    assert (decision.status, decision.timing_state, decision.acceptance_blocking) == ("OK", "CURRENT", False)


def test_stale_transient_workflow_label_cannot_override_authoritative_current_state():
    decision = evaluate_boundary_health(
        run(available=True),
        candle_available=True,
        now=BOUNDARY + timedelta(seconds=5),
    )
    assert (decision.status, decision.timing_state) == ("OK", "CURRENT")


def test_transient_workflow_label_cannot_mask_authoritative_degradation():
    decision = evaluate_boundary_health(
        run(health="GAP_DETECTED", blocker_kind="HEALTH_STATUS_NOT_OK", blocker_code="STATUS_GAP_DETECTED"),
        candle_available=True,
        now=BOUNDARY + timedelta(seconds=5),
    )
    assert decision.status == "DEGRADED"


@pytest.mark.parametrize(
    "value",
    [
        SimpleNamespace(status="WAITING_FOR_REQUIRED_BOUNDARY", error_code=None, last_freshness_payload=None),
        SimpleNamespace(status="WAITING_FOR_REQUIRED_BOUNDARY", error_code=None, last_freshness_payload={"timeframes": "invalid"}),
    ],
)
def test_missing_authoritative_fields_are_safe_unknown(value):
    decision = evaluate_boundary_health(value, candle_available=True, now=BOUNDARY)
    assert (decision.status, decision.acceptance_blocking) == ("UNKNOWN", True)


def test_missing_boundary_blocker_evidence_cannot_be_false_ok():
    value = run()
    value.last_freshness_payload["blocking_reasons"] = []
    decision = evaluate_boundary_health(value, candle_available=True, now=BOUNDARY)
    assert (decision.status, decision.acceptance_blocking) == ("UNKNOWN", True)


def test_unsupported_timeframe_cannot_be_false_ok():
    decision = evaluate_boundary_health(
        run(timeframe="2h"), candle_available=True, now=BOUNDARY
    )
    assert (decision.status, decision.acceptance_blocking) == ("DEGRADED", True)


def test_clock_must_be_utc_aware():
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_boundary_health(run(), candle_available=True, now=BOUNDARY.replace(tzinfo=None))


def test_missing_candle_and_active_orchestrator_error_are_blocking():
    missing = evaluate_boundary_health(run(), candle_available=False, now=BOUNDARY)
    error = evaluate_boundary_health(
        run(run_status="ERROR", error_code="ACTIVE_ERROR"),
        candle_available=True,
        now=BOUNDARY,
    )
    assert missing.status == "NOT_AVAILABLE"
    assert error.status == "ERROR"
    assert missing.acceptance_blocking and error.acceptance_blocking


def test_repository_maps_original_failure_to_consistent_non_blocking_health():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions.begin() as session:
        session.add(Candle15m(
            id=1,
            symbol="BTCUSDT",
            open_time_ms=BOUNDARY_MS - 900_000,
            close_time_ms=BOUNDARY_MS - 1,
            open_time_utc=BOUNDARY - timedelta(minutes=15),
            close_time_utc=BOUNDARY - timedelta(milliseconds=1),
            open=1,
            high=1,
            low=1,
            close=1,
            volume=1,
            source="test",
            is_closed=True,
            updated_at_utc=BOUNDARY + timedelta(seconds=50),
        ))
        waiting = run()
        session.add(OnlinePipelineRun(
            run_id="health-boundary-test",
            symbol="BTCUSDT",
            primary_timeframe="15m",
            closed_until_ms=BOUNDARY_MS,
            closed_until_utc=BOUNDARY,
            status=waiting.status,
            trigger_source="test",
            daemon_instance_id="test",
            market_data_freshness_status=waiting.market_data_freshness_status,
            last_freshness_payload=waiting.last_freshness_payload,
            future_bars_used=False,
            is_trade_signal=False,
            is_executable=False,
            order_approved=False,
            execution_approved=False,
            position_opened=False,
            position_size_approved=False,
            updated_at=BOUNDARY + timedelta(seconds=50),
        ))

    adapter = SqlAlchemyReadAdapter(
        sessions,
        clock=lambda: BOUNDARY + timedelta(seconds=51),
    )
    value = adapter.get_health()
    assert value.status == "OK"
    assert value.timing_state == "WITHIN_GRACE"
    assert value.operational and value.ready
    assert value.acceptance_blocking is False
    assert {item.status for item in value.services} == {"OK"}
