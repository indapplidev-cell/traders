from datetime import datetime, timedelta, timezone
from app.engine_observation.integrity_auditor import audit_integrity
from tests.engine_observation_01_helpers import result, run


def test_orphan_stale_negative_and_transition_detection():
    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    stale = run(status="RUNNING", started_at=now - timedelta(minutes=10), finished_at=None,
                duration_ms=-1, analysis_status=None, setup_status=None, strategy_status=None,
                risk_status=None, paper_status=None, final_result=None)
    orphan = result(stale, run_id="orphan")
    audit = audit_integrity([stale], [orphan], now=now)
    assert audit["checks"]["orphan_result_rows"] == 1
    assert audit["checks"]["stale_reservations"] == 1
    assert audit["checks"]["negative_duration"] == 1


def test_invalid_transition_detected():
    r = run(setup_status="NO_SETUP", strategy_status="ALLOW")
    assert audit_integrity([r], [result(r)])["checks"]["invalid_transitions"] == 1
