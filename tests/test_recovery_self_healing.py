from datetime import datetime, timezone, timedelta
import json
import subprocess
from dataclasses import replace
import pytest
from app.engine_safety.recovery_state import RecoveryState
from app.server_api.paper_runtime_observation import _pitr_lineage
from tests.readonly_production_runtime_observation.test_observation import _recovery
from scripts import production_wal_archive_remediation as daemon


def test_real_chain_recheck_recovers_without_restart(tmp_path, monkeypatch):
    now=datetime.now(timezone.utc)
    _recovery(tmp_path,now=now)
    monkeypatch.setattr(daemon,"SAFE_ROOT",tmp_path)
    calls=[]
    def cycle(root,process_id):
        calls.append(process_id)
        if len(calls)==1:
            raise subprocess.TimeoutExpired("isolated",1)
        return dict(schema="TRADERS_ML_WAL_ACK_DAEMON_STATE_V1",status="RUNNING",error_class="NONE",export_backlog_count=0,pending_archive_status_count=0,updated_at=datetime.now(timezone.utc).isoformat(),process_id=process_id)
    monkeypatch.setattr(daemon,"_host_ack_daemon_cycle",cycle)
    transitions=[]
    def wait(seconds):
        doc=json.loads((tmp_path/"catalog/recovery_readiness.json").read_text())
        transitions.append(doc)
        if len(transitions)==2: raise KeyboardInterrupt
    monkeypatch.setattr(daemon.time,"sleep",wait)
    with pytest.raises(KeyboardInterrupt): daemon.run_host_ack_daemon(tmp_path,interval_seconds=daemon._DAEMON_POLICY.interval_seconds)
    assert len(set(calls))==1
    assert transitions[0]["wal"]["state"]=="DEGRADED"
    assert transitions[1]["wal"]["state"]=="READY"
    assert transitions[1]["pitr"]["state"]=="READY"
    assert transitions[1]["wal"]["last_failure_at"]
    assert transitions[1]["wal"]["recovered_at"]
    assert transitions[1]["wal"]["next_recheck_at"]


def test_real_gap_never_becomes_ready(tmp_path):
    now=datetime.now(timezone.utc)
    _recovery(tmp_path,now=now,gap=True)
    for _ in range(2):
        value=_pitr_lineage(tmp_path,now)
        assert not value.pitr_ready
        assert value.pitr_state=="BLOCKED"
        assert value.pitr_reason_code=="PITR_WAL_GAP"


def test_stale_heartbeat_is_distinct_from_quiet_archive(tmp_path):
    now=datetime.now(timezone.utc)
    _recovery(tmp_path,now=now)
    assert _pitr_lineage(tmp_path,now).wal_ready
    stale=_pitr_lineage(tmp_path,now+timedelta(seconds=daemon.RUNTIME_POLICY.paper_readiness.wal_daemon_max_age_seconds+1))
    assert stale.wal_reason_code=="WAL_ARCHIVE_STALE"
    assert stale.lineage_valid


def test_transition_log_only_changes(caplog):
    now=datetime.now(timezone.utc)
    with caplog.at_level("INFO"):
        state=RecoveryState().advance("READY","WAL_ARCHIVE_READY",now,3)
        state=state.advance("READY","WAL_ARCHIVE_READY",now,3)
    assert len(caplog.records)==1


def _worker_state(now, **changes):
    value = {
        "heartbeat_at": now.isoformat(),
        "next_recheck_at": (now + timedelta(seconds=3)).isoformat(),
        "instance_id": "current", "generation": 2,
    }
    value.update(changes)
    return value


def test_dead_worker_is_primary_cause():
    now=datetime.now(timezone.utc)
    assert daemon.classify_worker_health(_worker_state(now),now=now,process_alive=False) == (False,"RECOVERY_WORKER_NOT_RUNNING")


def test_stale_worker_heartbeat_is_detected():
    now=datetime.now(timezone.utc)
    old=now-timedelta(seconds=daemon._DAEMON_POLICY.heartbeat_freshness_seconds+1)
    assert daemon.classify_worker_health(_worker_state(now,heartbeat_at=old.isoformat()),now=now,process_alive=True)[1] == "RECOVERY_HEARTBEAT_STALE"


def test_overdue_recheck_is_detected():
    now=datetime.now(timezone.utc)
    old=now-timedelta(seconds=daemon._DAEMON_POLICY.recheck_grace_seconds+1)
    assert daemon.classify_worker_health(_worker_state(now,next_recheck_at=old.isoformat()),now=now,process_alive=True)[1] == "RECOVERY_RECHECK_STALLED"


def test_current_worker_health_passes():
    now=datetime.now(timezone.utc)
    assert daemon.classify_worker_health(_worker_state(now),now=now,process_alive=True) == (True,"RECOVERY_WORKER_READY")


def test_stale_running_is_invalidated_by_new_generation():
    now=datetime.now(timezone.utc)
    old=RecoveryState(state="READY",instance_id="old",generation=1,heartbeat_at=now.isoformat())
    new=old.bind("new",2,now,3)
    assert (new.state,new.reason_code,new.instance_id,new.generation)==("RECOVERING","RECOVERY_WORKER_STARTING","new",2)


def test_old_generation_heartbeat_cannot_masquerade_as_current():
    now=datetime.now(timezone.utc)
    state=_worker_state(now,instance_id="old",generation=1)
    assert not (state["instance_id"]=="new" and state["generation"]==2)


def test_recheck_rearms_after_transient_failure_and_success():
    now=datetime.now(timezone.utc)
    failed=RecoveryState().advance("DEGRADED","WAL_ARCHIVER_FAILURE",now,3)
    ready=failed.advance("READY","WAL_ARCHIVE_READY",now+timedelta(seconds=3),3)
    assert failed.next_recheck_at and ready.next_recheck_at and ready.recovered_at


def test_recheck_timestamps_belong_to_the_same_iteration():
    first_started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first_finished = first_started + timedelta(seconds=2)
    second_started = first_finished + timedelta(seconds=3)
    second_finished = second_started + timedelta(seconds=1)
    state = RecoveryState().advance(
        "READY", "WAL_ARCHIVE_READY", first_finished, 10,
        recheck_started_at=first_started,
    )
    state = state.advance(
        "READY", "WAL_ARCHIVE_READY", second_finished, 10,
        recheck_started_at=second_started,
    )
    assert state.last_recheck_started_at == second_started.isoformat()
    assert state.last_recheck_finished_at == second_finished.isoformat()
    assert state.last_recheck_started_at <= state.last_recheck_finished_at
    assert state.next_recheck_at == (second_finished + timedelta(seconds=10)).isoformat()
    assert state.heartbeat_at == second_finished.isoformat()
    assert state.snapshot_generated_at == second_finished.isoformat()


def test_three_repeated_recovery_cycles_are_not_sticky():
    now=datetime.now(timezone.utc)
    state=RecoveryState()
    for cycle in range(3):
        state=state.advance("DEGRADED","WAL_ARCHIVER_FAILURE",now+timedelta(seconds=cycle*6),3)
        state=state.advance("RECOVERING","PITR_VERIFICATION_PENDING",now+timedelta(seconds=cycle*6+2),3)
        state=state.advance("READY","WAL_ARCHIVE_READY",now+timedelta(seconds=cycle*6+3),3)
        assert state.state=="READY" and state.next_recheck_at
