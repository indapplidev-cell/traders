"""Recovery domains never substitute for PostgreSQL transaction durability."""
from dataclasses import dataclass
from sqlalchemy import text

@dataclass(frozen=True, slots=True)
class DatabaseReadiness:
    runtime_ready: bool = False
    durability_ready: bool = False
    reason_code: str = "DATABASE_NOT_EVALUATED"

def observe_database(session_factory):
    """Read actual server durability settings; never issue a probe mutation."""
    try:
        with session_factory() as session:
            row = session.execute(text("SELECT NOT pg_is_in_recovery(), current_setting('transaction_read_only') = 'off', current_setting('fsync') = 'on', current_setting('full_page_writes') = 'on', current_setting('synchronous_commit') IN ('on','remote_apply','remote_write'), pg_current_wal_lsn() IS NOT NULL, NOT EXISTS (SELECT 1 FROM pg_db_role_setting s, unnest(s.setconfig) c WHERE (s.setrole=0 OR s.setrole=(SELECT oid FROM pg_roles WHERE rolname='traders_paper_runtime')) AND (s.setdatabase=0 OR s.setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database())) AND c IN ('default_transaction_read_only=on','synchronous_commit=off','synchronous_commit=local'))")).one()
        durable = all(row)
        return DatabaseReadiness(True, durable, "DATABASE_DURABILITY_READY" if durable else "DATABASE_DURABILITY_BLOCKED")
    except Exception:
        return DatabaseReadiness(False, False, "DATABASE_UNAVAILABLE")

def live_durability_ready(paper_ready, wal_ready, pitr_ready, live_guards):
    return all((paper_ready, wal_ready, pitr_ready, live_guards))
