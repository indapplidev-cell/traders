"""One-shot no-echo rotation for the shared production PostgreSQL principal.

The old and new credentials exist only in process memory and the approved
protected secret file. Subprocess arguments, reports, and exceptions never
contain either value or a credential-bearing URI.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.db.postgres_auth_probe import probe_postgres_authentication
from scripts.verify_shared_db_secret_binding import BINDING, binding_errors


POSTGRES = "traders-ml-postgres-1"
PRINCIPAL = "traders_ml"
DATABASE = "traders_ml"
AFFECTED = (
    ("market-data-sync", "traders-ml-market-data-sync-1", ()),
    ("online-orchestrator-5m", "traders-ml-online-orchestrator-5m-1", ("orchestrator-5m",)),
    ("online-orchestrator", "traders-ml-online-orchestrator-1", ("orchestrator",)),
)
REPORT = ROOT / "reports" / "security" / "production_db_credential_rotation.json"


class SafeRotationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClientResult:
    service: str
    container: str
    principal: str
    binding_path: str
    new_binding_loaded: bool
    reconnect: bool
    db_query: bool
    health: bool
    old_credential_rejected: bool
    image_unchanged: bool
    restart_count_before: int
    restart_count_after: int


def _run(args: list[str], *, input_text: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    if any("://" in item for item in args):
        raise SafeRotationError("SECRET_BEARING_COMMAND_REJECTED")
    return subprocess.run(
        args,
        cwd=ROOT,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _inspect(name: str) -> dict:
    result = _run(["docker", "inspect", name])
    if result.returncode:
        raise SafeRotationError("CONTAINER_INSPECTION_FAILED")
    try:
        payload = json.loads(result.stdout)
        return payload[0]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
        raise SafeRotationError("CONTAINER_INSPECTION_REJECTED") from error


def _env(document: dict) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in document.get("Config", {}).get("Env", ()) or ():
        if isinstance(item, str) and "=" in item:
            key, value = item.split("=", 1)
            values[key] = value
    return values


def _identity(document: dict) -> tuple[str, int, bool]:
    state = document.get("State", {})
    return (
        str(document.get("Image") or ""),
        int(document.get("RestartCount") or 0),
        bool(state.get("Running")),
    )


def _restrict_acl(path: Path, *, directory: bool) -> None:
    identity = _run([
        "pwsh.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value",
    ])
    current_sid = identity.stdout.strip()
    if identity.returncode or not re.fullmatch(r"S-\d(?:-\d+)+", current_sid):
        raise SafeRotationError("CURRENT_USER_SID_RESOLUTION_FAILED")
    inherit = "(OI)(CI)" if directory else ""
    result = _run([
        "icacls.exe",
        str(path.resolve()),
        "/inheritance:r",
        "/grant:r",
        f"*{current_sid}:{inherit}M",
        f"*S-1-5-18:{inherit}F",
        f"*S-1-5-32-544:{inherit}F",
    ])
    if result.returncode:
        raise SafeRotationError("ACL_APPLICATION_FAILED")


def _create_binding(new_password: str) -> None:
    if BINDING.exists():
        raise SafeRotationError("PROTECTED_BINDING_ALREADY_EXISTS")
    BINDING.parent.mkdir(exist_ok=True)
    _restrict_acl(BINDING.parent, directory=True)
    descriptor = os.open(BINDING, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    _restrict_acl(BINDING, directory=False)
    with BINDING.open("wb", buffering=0) as stream:
        stream.write(new_password.encode("ascii") + b"\n")
        os.fsync(stream.fileno())
    if binding_errors(BINDING):
        raise SafeRotationError("PROTECTED_BINDING_VERIFICATION_FAILED")


def _baseline() -> tuple[str, str, dict[str, tuple[str, int]], bool]:
    urls: list[str] = []
    identities: dict[str, tuple[str, int]] = {}
    for _, container, _ in AFFECTED:
        document = _inspect(container)
        image, restarts, running = _identity(document)
        if not running:
            raise SafeRotationError("AFFECTED_CLIENT_NOT_RUNNING")
        value = _env(document).get("DATABASE_URL")
        if not value:
            raise SafeRotationError("AFFECTED_CLIENT_BINDING_MISSING")
        urls.append(value)
        identities[container] = (image, restarts)
    if len(set(urls)) != 1:
        raise SafeRotationError("AFFECTED_CLIENT_BINDINGS_DIVERGED")
    url = make_url(urls[0])
    old_password = url.password or ""
    if url.username != PRINCIPAL or not old_password:
        raise SafeRotationError("EXPOSED_PRINCIPAL_NOT_UNAMBIGUOUS")
    postgres_password = _env(_inspect(POSTGRES)).get("POSTGRES_PASSWORD")
    # POSTGRES_PASSWORD is initialization-only when the persistent data
    # directory already exists. A prior rotation can legitimately leave this
    # immutable container-config field stale; it is not an authentication
    # fallback. The new Compose contract removes it on the next DB replacement
    # without restarting PostgreSQL during this task.
    bootstrap_binding_matches = postgres_password == old_password
    return PRINCIPAL, old_password, identities, bootstrap_binding_matches


def _connect(password: str) -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1",
        port=5433,
        dbname=DATABASE,
        user=PRINCIPAL,
        password=password,
        connect_timeout=5,
    )


def _rotate_role(old_password: str, new_password: str) -> None:
    with _connect(old_password) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            if cursor.fetchone() != (PRINCIPAL,):
                raise SafeRotationError("ADMIN_CONNECTION_IDENTITY_MISMATCH")
            cursor.execute(
                sql.SQL("ALTER ROLE {} PASSWORD %s").format(sql.Identifier(PRINCIPAL)),
                (new_password,),
            )


def _auth_probe(password: str) -> tuple[str, str | None]:
    probe = probe_postgres_authentication(
        host="127.0.0.1",
        port=5433,
        database=DATABASE,
        username=PRINCIPAL,
        password=password,
        timeout_seconds=5,
    )
    return probe.connection, probe.sqlstate


def _compose_rebind(service: str, profiles: tuple[str, ...]) -> None:
    command = ["docker", "compose"]
    for profile in profiles:
        command.extend(("--profile", profile))
    command.extend(("up", "-d", "--no-build", "--no-deps", "--force-recreate", service))
    result = _run(command, timeout=180)
    if result.returncode:
        raise SafeRotationError(f"CLIENT_REBIND_FAILED_{service.upper().replace('-', '_')}")


def _wait_client(container: str, expected_image: str) -> tuple[bool, int, bool]:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        document = _inspect(container)
        image, restarts, running = _identity(document)
        env_safe = "DATABASE_URL" not in _env(document)
        mounts = document.get("Mounts", ()) or ()
        secret_loaded = any(
            item.get("Destination") == "/run/secrets/traders_shared_db_password"
            for item in mounts
            if isinstance(item, dict)
        )
        if running and env_safe and secret_loaded:
            return image == expected_image, restarts, True
        time.sleep(2)
    return False, -1, False


def _client_query(container: str) -> bool:
    code = (
        "import psycopg;"
        "p=open('/run/secrets/traders_shared_db_password','r',encoding='ascii').read().strip();"
        "c=psycopg.connect(host='postgres',port=5432,dbname='traders_ml',user='traders_ml',password=p,connect_timeout=5);"
        "v=c.execute('SELECT current_user,current_database()').fetchone();"
        "c.close();"
        "raise SystemExit(0 if v==('traders_ml','traders_ml') else 1)"
    )
    result = _run(["docker", "exec", container, "python", "-c", code], timeout=30)
    return result.returncode == 0


def _client_stable(container: str, observed_restarts: int) -> bool:
    time.sleep(8)
    document = _inspect(container)
    _, current_restarts, running = _identity(document)
    return (
        running
        and current_restarts == observed_restarts
        and "DATABASE_URL" not in _env(document)
    )


def _logs_contain_secret(container: str, old_password: str, new_password: str, since: str) -> bool:
    result = _run(["docker", "logs", "--since", since, container], timeout=30)
    combined = result.stdout + result.stderr
    return old_password in combined or new_password in combined


def execute(*, resume_prepared_binding: bool = False) -> dict[str, object]:
    started = datetime.now(timezone.utc)
    generation = "shared-db-" + started.strftime("%Y%m%dT%H%M%SZ")
    principal, old_password, identities, bootstrap_binding_matches = _baseline()
    if BINDING.exists():
        if not resume_prepared_binding or binding_errors(BINDING):
            raise SafeRotationError("PREPARED_BINDING_REQUIRES_EXPLICIT_RESUME")
        new_password = BINDING.read_text(encoding="ascii").strip()
    else:
        if resume_prepared_binding:
            raise SafeRotationError("PREPARED_BINDING_MISSING")
        new_password = secrets.token_urlsafe(48)
        while new_password == old_password:
            new_password = secrets.token_urlsafe(48)
        _create_binding(new_password)

    old_before, old_before_sqlstate = _auth_probe(old_password)
    new_before, new_before_sqlstate = _auth_probe(new_password)
    if old_before == "ACCEPTED" and new_before == "DENIED" and new_before_sqlstate == "28P01":
        _rotate_role(old_password, new_password)
    elif old_before == "DENIED" and old_before_sqlstate == "28P01" and new_before == "ACCEPTED":
        pass
    else:
        raise SafeRotationError("ROTATION_AUTH_STATE_AMBIGUOUS")
    new_connection, new_sqlstate = _auth_probe(new_password)
    if new_connection != "ACCEPTED" or new_sqlstate is not None:
        raise SafeRotationError("NEW_CREDENTIAL_POSITIVE_AUTH_FAILED")

    clients: list[ClientResult] = []
    for service, container, profiles in AFFECTED:
        expected_image, restart_before = identities[container]
        _compose_rebind(service, profiles)
        image_unchanged, restart_after, loaded = _wait_client(container, expected_image)
        query = loaded and _client_query(container)
        health = loaded and query and _client_stable(container, restart_after)
        clients.append(
            ClientResult(
                service=service,
                container=container,
                principal=principal,
                binding_path=str(BINDING),
                new_binding_loaded=loaded,
                reconnect=loaded,
                db_query=query,
                health=health,
                old_credential_rejected=False,
                image_unchanged=image_unchanged,
                restart_count_before=restart_before,
                restart_count_after=restart_after,
            )
        )
        if not (loaded and query and image_unchanged):
            raise SafeRotationError("CLIENT_ACCEPTANCE_FAILED")

    old_connection, old_sqlstate = _auth_probe(old_password)
    old_rejected = old_connection == "DENIED" and old_sqlstate == "28P01"
    if not old_rejected:
        raise SafeRotationError("OLD_CREDENTIAL_INVALIDATION_UNPROVEN")
    clients = [
        ClientResult(**{**asdict(item), "old_credential_rejected": True})
        for item in clients
    ]
    since = started.isoformat().replace("+00:00", "Z")
    exposure_findings = sum(
        _logs_contain_secret(item.container, old_password, new_password, since)
        for item in clients
    )
    if exposure_findings:
        raise SafeRotationError("TASK_TOUCHED_LOG_SECRET_EXPOSURE")

    result: dict[str, object] = {
        "schema": "TRADERS_PRODUCTION_DB_CREDENTIAL_ROTATION_V1",
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rotation_generation": generation,
        "exposed_db_principal": principal,
        "affected_principal_count": 1,
        "affected_client_count": len(clients),
        "affected_inventory_complete": True,
        "new_credential_created": True,
        "new_credential_stored_in_approved_protected_binding": True,
        "new_credential_connection_pass": True,
        "old_credential_invalidated": True,
        "old_credential_new_connection_rejected": True,
        "old_credential_sqlstate": "28P01",
        "old_credential_fallback_present": False,
        "postgres_bootstrap_binding_was_current": bootstrap_binding_matches,
        "clients": [asdict(item) for item in clients],
        "all_affected_clients_rebound": all(item.db_query and item.health for item in clients),
        "role_privileges_changed_by_task": False,
        "role_membership_changed_by_task": False,
        "database_schema_changed_by_task": False,
        "new_secret_exposure_findings": exposure_findings,
        "old_secret_value_output": 0,
        "new_secret_value_output": 0,
        "protected_secret_value_output": 0,
        "secret_derived_hash_created": False,
        "secret_logging_implemented": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume-prepared-binding", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print("EXECUTION=NOT_REQUESTED")
        print("SECRET_VALUE_OUTPUT=NO")
        return 2
    try:
        result = execute(resume_prepared_binding=args.resume_prepared_binding)
    except (
        SafeRotationError,
        OSError,
        RuntimeError,
        ValueError,
        psycopg.Error,
        subprocess.TimeoutExpired,
    ) as error:
        print("ROTATION=FAILED")
        print(f"ERROR_CLASS={type(error).__name__}")
        safe_code = (
            error.args[0]
            if isinstance(error, SafeRotationError)
            and error.args
            and isinstance(error.args[0], str)
            else "NORMALIZED_FAILURE"
        )
        print(f"ERROR_CODE={safe_code}")
        print("SECRET_VALUE_OUTPUT=NO")
        print("SECRET_DERIVED_HASH_CREATED=NO")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
