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
