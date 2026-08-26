"""No-echo rotation of every DB principal exposed by production env inspection.

The controller keeps credentials only in memory and approved protected binding
files.  Reports contain role names, structural binding identities, catalog
privileges, auth outcomes and restart identities; they never contain a
credential, URI, exception message, hash, length, prefix or suffix.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.db.postgres_auth_probe import probe_postgres_authentication
from app.engine_paper.production_preparation_backend import (
    PRODUCTION_PROTECTED_SOURCE,
    _atomic_write,
    _parse_env_binding,
    _render_env_binding,
)
from scripts.production_db_credential_rotation import (
    AFFECTED as SHARED_CLIENTS,
    BINDING as SHARED_BINDING,
    _create_binding,
    _restrict_acl,
)
from scripts.safe_docker_inspection import (
    SafeContainerInspection,
    SafeDockerInspectionError,
    safe_inspect_container,
)
from scripts.verify_shared_db_secret_binding import binding_errors


POSTGRES = "traders-ml-postgres-1"
DATABASE = "traders_ml"
HOST = "127.0.0.1"
PORT = 5433
ROLES = ("traders_readonly_api", "traders_paper_runtime", "traders_ml")
ENV_URL_KEYS = (
    "DATABASE_URL",
    "MARKET_DATA_DATABASE_URL",
    "TRADERS_READONLY_API_DATABASE_URL",
    "TRADERS_PAPER_RUNTIME_DATABASE_URL",
)
ROLE_URL_KEYS = {
    "traders_ml": ("DATABASE_URL",),
    "traders_readonly_api": ("TRADERS_READONLY_API_DATABASE_URL",),
    "traders_paper_runtime": ("TRADERS_PAPER_RUNTIME_DATABASE_URL",),
}
ADMIN_PASSWORD_KEY = "TRADERS_ML_POSTGRES_PASSWORD"
READONLY_CONTAINER = "traders-readonly-api-readonly-api-1"
CONTROL_CONTAINER = "traders-operator-control-api-operator-control-api-1"
REPORT = ROOT / "reports" / "security" / "production_db_security_remediation.json"
PREFLIGHT_REPORT = ROOT / "reports" / "security" / "production_db_security_preflight.json"
SHARED_PENDING = SHARED_BINDING.with_name(SHARED_BINDING.name + ".security-next")
ENV_PENDING = PRODUCTION_PROTECTED_SOURCE.with_name(
    PRODUCTION_PROTECTED_SOURCE.name + ".security-next"
)


class SafeRemediationError(RuntimeError):
    pass


def _run(args: list[str], *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    if any("://" in item for item in args):
        raise SafeRemediationError("SECRET_BEARING_COMMAND_REJECTED")
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SafeRemediationError("NORMALIZED_SUBPROCESS_FAILURE") from None


def _inspect(name: str) -> SafeContainerInspection:
    try:
        return safe_inspect_container(name)
    except SafeDockerInspectionError:
        raise SafeRemediationError("SAFE_CONTAINER_INSPECTION_FAILED") from None


def _load_bindings() -> tuple[dict[str, str], dict[str, str], tuple[str, ...]]:
    if binding_errors(SHARED_BINDING):
        raise SafeRemediationError("SHARED_BINDING_INVALID")
    try:
        shared = SHARED_BINDING.read_text(encoding="ascii").strip()
        values = _parse_env_binding(PRODUCTION_PROTECTED_SOURCE.read_text(encoding="utf-8"))
    except Exception:
        raise SafeRemediationError("PROTECTED_BINDING_READ_FAILED") from None
    if not shared:
        raise SafeRemediationError("SHARED_BINDING_EMPTY")
    candidates: dict[str, list[tuple[str, bool]]] = {
        "traders_ml": [(shared, False)]
    }
    for role, keys in ROLE_URL_KEYS.items():
        for key in keys:
            value = values.get(key)
            if not value:
                raise SafeRemediationError(f"REQUIRED_ROLE_BINDING_MISSING_{key}")
            try:
                url = make_url(value)
            except Exception:
                raise SafeRemediationError("REQUIRED_ROLE_BINDING_INVALID") from None
            if url.username != role or not url.password:
                raise SafeRemediationError("REQUIRED_ROLE_BINDING_IDENTITY_MISMATCH")
            candidates.setdefault(role, []).append((url.password, True))
    admin_candidate = values.get(ADMIN_PASSWORD_KEY)
    if not admin_candidate:
        raise SafeRemediationError("ADMIN_PASSWORD_BINDING_MISSING")
    candidates["traders_ml"].append((admin_candidate, True))
    passwords: dict[str, str] = {}
    exposed_active: list[str] = []
    for role in ROLES:
        unique: list[tuple[str, bool]] = []
        for candidate, exposed in candidates.get(role, []):
            matching = next((index for index, item in enumerate(unique) if item[0] == candidate), None)
            if matching is None:
                unique.append((candidate, exposed))
            elif exposed and not unique[matching][1]:
                unique[matching] = (candidate, True)
        active = [item for item in unique if _auth(role, item[0]) == ("CONNECTED", None)]
        if len(active) != 1:
            raise SafeRemediationError("ACTIVE_ROLE_CREDENTIAL_AMBIGUOUS")
        passwords[role] = active[0][0]
        if active[0][1]:
            exposed_active.append(role)
    if len(exposed_active) < 2:
        raise SafeRemediationError("REPORTED_MULTI_PRINCIPAL_SCOPE_NOT_CORROBORATED")
    return values, passwords, tuple(role for role in ROLES if role in exposed_active)


def _connect(role: str, password: str) -> psycopg.Connection[Any]:
    return psycopg.connect(
        host=HOST,
        port=PORT,
        dbname=DATABASE,
        user=role,
        password=password,
        connect_timeout=5,
    )


def _auth(role: str, password: str) -> tuple[str, str | None]:
    probe = probe_postgres_authentication(
        host=HOST,
        port=PORT,
        database=DATABASE,
        username=role,
        password=password,
        timeout_seconds=5,
    )
    return probe.connection, probe.sqlstate


def _catalog_snapshot(admin_password: str) -> dict[str, Any]:
    role_placeholders = sql.SQL(",").join(sql.Literal(role) for role in ROLES)
    with _connect("traders_ml", admin_password) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT rolname,rolsuper,rolcreatedb,rolcreaterole,rolreplication,"
                    "rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname IN ({}) ORDER BY rolname"
                ).format(role_placeholders)
            )
            attributes = [
                dict(zip(("role", "superuser", "createdb", "createrole", "replication", "bypass_rls", "can_login"), row))
                for row in cursor.fetchall()
            ]
            cursor.execute(
                sql.SQL(
                    "SELECT member.rolname, parent.rolname FROM pg_auth_members m "
                    "JOIN pg_roles member ON member.oid=m.member "
                    "JOIN pg_roles parent ON parent.oid=m.roleid "
                    "WHERE member.rolname IN ({}) ORDER BY 1,2"
                ).format(role_placeholders)
            )
            memberships = [list(row) for row in cursor.fetchall()]
            cursor.execute(
                sql.SQL(
                    "SELECT grantee,table_schema,table_name,privilege_type,is_grantable "
                    "FROM information_schema.role_table_grants WHERE grantee IN ({}) "
                    "ORDER BY 1,2,3,4,5"
                ).format(role_placeholders)
            )
            table_grants = [list(row) for row in cursor.fetchall()]
            cursor.execute(
                sql.SQL(
                    "SELECT grantee,routine_schema,routine_name,privilege_type,is_grantable "
                    "FROM information_schema.role_routine_grants WHERE grantee IN ({}) "
                    "ORDER BY 1,2,3,4,5"
                ).format(role_placeholders)
            )
            routine_grants = [list(row) for row in cursor.fetchall()]
            cursor.execute("SELECT version_num FROM alembic_version")
            alembic = cursor.fetchone()[0]
    return {
        "role_attributes": attributes,
        "memberships": memberships,
        "table_grants": table_grants,
        "routine_grants": routine_grants,
        "alembic": alembic,
    }


def _business_counts(admin_password: str) -> dict[str, int]:
    tables = (
        "paper_execution_commands",
        "paper_orders",
        "paper_fills",
        "paper_positions",
    )
    counts: dict[str, int] = {}
    with _connect("traders_ml", admin_password) as connection:
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(
                    sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
                )
                counts[table] = int(cursor.fetchone()[0])
    return counts


def preflight() -> dict[str, Any]:
    _values, passwords, exposed_roles = _load_bindings()
    auth = {
        role: _auth(role, passwords[role]) == ("CONNECTED", None)
        for role in ROLES
    }
    if not all(auth.values()):
        raise SafeRemediationError("PREFLIGHT_AUTH_FAILED")
    containers = {
        name: asdict(_inspect(name))
        for name in (
            POSTGRES,
            *(container for _, container, _ in SHARED_CLIENTS),
            READONLY_CONTAINER,
            CONTROL_CONTAINER,
        )
    }
    result = {
        "schema": "TRADERS_PRODUCTION_DB_SECURITY_PREFLIGHT_V1",
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "incident_scope_identified": True,
        "exposed_db_principals": list(exposed_roles),
        "exposed_db_principal_count": len(exposed_roles),
        "affected_consumer_count": 2 + (3 if "traders_ml" in exposed_roles else 0),
        "current_credentials_authenticate": auth,
        "catalog": _catalog_snapshot(passwords["traders_ml"]),
        "business_counts": _business_counts(passwords["traders_ml"]),
        "containers": containers,
        "secret_output": 0,
        "secret_derived_hash_created": False,
    }
    PREFLIGHT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PREFLIGHT_REPORT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _prepare_bindings(
    values: dict[str, str], new_passwords: dict[str, str], target_roles: tuple[str, ...]
) -> None:
    if ENV_PENDING.exists() or ("traders_ml" in target_roles and SHARED_PENDING.exists()):
        raise SafeRemediationError("STALE_PENDING_BINDING_PRESENT")
    updated = dict(values)
    if "traders_ml" in target_roles:
        updated[ADMIN_PASSWORD_KEY] = new_passwords["traders_ml"]
    for role in target_roles:
        keys = ROLE_URL_KEYS[role]
        for key in keys:
            updated[key] = make_url(values[key]).set(password=new_passwords[role]).render_as_string(hide_password=False)
    if "traders_ml" in target_roles:
        _create_binding(SHARED_PENDING, new_passwords["traders_ml"])
    _atomic_write(ENV_PENDING, _render_env_binding(updated), template=PRODUCTION_PROTECTED_SOURCE)


def _rotate_roles(
    old_passwords: dict[str, str],
    new_passwords: dict[str, str],
    target_roles: tuple[str, ...],
) -> None:
    with _connect("traders_ml", old_passwords["traders_ml"]) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            for role in target_roles:
                old_state, _ = _auth(role, old_passwords[role])
                new_state, new_sqlstate = _auth(role, new_passwords[role])
                if old_state != "CONNECTED" or new_state != "DENIED" or new_sqlstate != "28P01":
                    raise SafeRemediationError("PRE_ROTATION_AUTH_STATE_AMBIGUOUS")
                cursor.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(role), sql.Literal(new_passwords[role])
                    )
                )
                if _auth(role, new_passwords[role]) != ("CONNECTED", None):
                    raise SafeRemediationError("NEW_CREDENTIAL_AUTH_FAILED")
                if _auth(role, old_passwords[role]) != ("DENIED", "28P01"):
                    raise SafeRemediationError("OLD_CREDENTIAL_DENIAL_FAILED")


def _publish_bindings(target_roles: tuple[str, ...]) -> None:
    if "traders_ml" in target_roles:
        os.replace(SHARED_PENDING, SHARED_BINDING)
        _restrict_acl(SHARED_BINDING, directory=False)
    os.replace(ENV_PENDING, PRODUCTION_PROTECTED_SOURCE)
    if binding_errors(SHARED_BINDING):
        raise SafeRemediationError("PUBLISHED_SHARED_BINDING_INVALID")


def _rebind_consumers(target_roles: tuple[str, ...]) -> None:
    if "traders_ml" in target_roles:
        for service, _container, profiles in SHARED_CLIENTS:
            command = ["docker", "compose"]
            for profile in profiles:
                command.extend(("--profile", profile))
            command.extend(("up", "-d", "--no-build", "--no-deps", "--force-recreate", service))
            if _run(command).returncode:
                raise SafeRemediationError("SHARED_CONSUMER_REBIND_FAILED")
    commands = [
        ["docker", "compose", "-f", "ops/production/readonly-api/compose.yaml", "up", "-d", "--no-build", "--no-deps", "--force-recreate", "readonly-api"],
    ]
    if "traders_paper_runtime" in target_roles or "traders_ml" in target_roles:
        commands.append(
            ["docker", "compose", "-f", "ops/production/operator-control-api/compose.yaml", "up", "-d", "--no-build", "--no-deps", "--force-recreate", "operator-control-api"]
        )
    for command in commands:
        if _run(command).returncode:
            raise SafeRemediationError("ENV_CONSUMER_REBIND_FAILED")


def _wait_healthy(container: str, *, require_health: bool) -> SafeContainerInspection:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        inspection = _inspect(container)
        if inspection.state == "running" and (not require_health or inspection.health == "healthy"):
            return inspection
        time.sleep(2)
    raise SafeRemediationError("CONSUMER_HEALTH_TIMEOUT")


def _scan_logs(containers: tuple[str, ...], credentials: tuple[str, ...], since: str) -> int:
    findings = 0
    for container in containers:
        result = _run(["docker", "logs", "--since", since, container], timeout=30)
        payload = result.stdout + result.stderr
        if result.returncode or any(secret in payload for secret in credentials):
            findings += 1
    return findings


def execute() -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    values, old_passwords, target_roles = _load_bindings()
    before_catalog = _catalog_snapshot(old_passwords["traders_ml"])
    before = {
        name: _inspect(name)
        for name in (
            POSTGRES,
            *(container for _, container, _ in SHARED_CLIENTS),
            READONLY_CONTAINER,
            CONTROL_CONTAINER,
        )
    }
    new_passwords = {role: secrets.token_urlsafe(48) for role in target_roles}
    if len(set(new_passwords.values()) | set(old_passwords.values())) != len(new_passwords) + len(set(old_passwords.values())):
        raise SafeRemediationError("GENERATED_CREDENTIAL_COLLISION")
    _prepare_bindings(values, new_passwords, target_roles)
    _rotate_roles(old_passwords, new_passwords, target_roles)
    _publish_bindings(target_roles)
    _rebind_consumers(target_roles)
    after = {
        name: _wait_healthy(name, require_health=name in {POSTGRES, READONLY_CONTAINER, CONTROL_CONTAINER})
        for name in before
    }
    for role in target_roles:
        if _auth(role, new_passwords[role]) != ("CONNECTED", None):
            raise SafeRemediationError("FINAL_NEW_CREDENTIAL_AUTH_FAILED")
        if _auth(role, old_passwords[role]) != ("DENIED", "28P01"):
            raise SafeRemediationError("FINAL_OLD_CREDENTIAL_DENIAL_FAILED")
    admin_password_after = new_passwords.get("traders_ml", old_passwords["traders_ml"])
    after_catalog = _catalog_snapshot(admin_password_after)
    if before_catalog != after_catalog:
        raise SafeRemediationError("PRIVILEGE_OR_SCHEMA_MATRIX_CHANGED")
    containers = tuple(before)
    log_findings = _scan_logs(
        containers,
        tuple((*old_passwords.values(), *new_passwords.values())),
        started.isoformat().replace("+00:00", "Z"),
    )
    if log_findings:
        raise SafeRemediationError("TASK_LOG_SECRET_EXPOSURE")
    result: dict[str, Any] = {
        "schema": "TRADERS_PRODUCTION_DB_SECURITY_REMEDIATION_V1",
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rotation_generation": "db-security-" + started.strftime("%Y%m%dT%H%M%SZ"),
        "incident_scope_identified": True,
        "exposed_db_principals": list(target_roles),
        "exposed_db_principal_count": len(target_roles),
        "affected_consumers": (
            ["readonly-api", "operator-control-api"]
            + (["market-data", "orchestrator-15m", "orchestrator-5m"] if "traders_ml" in target_roles else [])
        ),
        "affected_consumer_count": 2 + (3 if "traders_ml" in target_roles else 0),
        "rotated_db_principal_count": len(target_roles),
        "old_credential_denied_count": len(target_roles),
        "new_credential_auth_success_count": len(target_roles),
        "privilege_matrix_before": before_catalog,
        "privilege_matrix_after": after_catalog,
        "privilege_matrix_preserved": True,
        "container_identity_before": {name: asdict(item) for name, item in before.items()},
        "container_identity_after": {name: asdict(item) for name, item in after.items()},
        "restart_or_replacement_count": sum(before[name].container_id != after[name].container_id for name in before),
        "postgres_restarted": before[POSTGRES].container_id != after[POSTGRES].container_id,
        "stale_active_secret_bindings": 0,
        "stale_active_consumers": 0,
        "new_secret_exposure_findings": 0,
        "secret_output_by_task": 0,
        "protected_secret_value_output": 0,
        "secret_derived_hash_created": False,
        "tracked_secret_created": False,
        "schema_mutations_by_task": 0,
        "privilege_expansion_by_task": 0,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight and not args.execute:
        try:
            result = preflight()
        except (SafeRemediationError, psycopg.Error, OSError, ValueError, TypeError) as error:
            print("PREFLIGHT=FAILED")
            print("ERROR_CLASS=NORMALIZED_SECURITY_PREFLIGHT_FAILURE")
            print(
                "ERROR_CODE="
                + (
                    str(error.args[0])
                    if isinstance(error, SafeRemediationError)
                    and error.args
                    and isinstance(error.args[0], str)
                    else "NORMALIZED_FAILURE"
                )
            )
            print("SECRET_VALUE_OUTPUT=NO")
            return 1
        print("PREFLIGHT=PASS")
        print(f"EXPOSED_DB_PRINCIPAL_COUNT={result['exposed_db_principal_count']}")
        print(f"AFFECTED_CONSUMER_COUNT={result['affected_consumer_count']}")
        print(f"PRODUCTION_ALEMBIC_HEAD={result['catalog']['alembic']}")
        print("SECRET_VALUE_OUTPUT=NO")
        return 0
    if not args.execute or args.preflight:
        print("EXECUTION=NOT_REQUESTED")
        print("SECRET_VALUE_OUTPUT=NO")
        return 2
    try:
        result = execute()
    except (SafeRemediationError, psycopg.Error, OSError, ValueError, TypeError) as error:
        print("ROTATION=FAILED")
        print("ERROR_CLASS=NORMALIZED_SECURITY_REMEDIATION_FAILURE")
        print(
            "ERROR_CODE="
            + (
                str(error.args[0])
                if isinstance(error, SafeRemediationError)
                and error.args
                and isinstance(error.args[0], str)
                else "NORMALIZED_FAILURE"
            )
        )
        print("SECRET_VALUE_OUTPUT=NO")
        print("SECRET_DERIVED_HASH_CREATED=NO")
        return 1
    print("ROTATION=PASS")
    print(f"ROTATED_DB_PRINCIPAL_COUNT={result['rotated_db_principal_count']}")
    print(f"OLD_CREDENTIAL_DENIED_COUNT={result['old_credential_denied_count']}")
    print(f"NEW_CREDENTIAL_AUTH_SUCCESS_COUNT={result['new_credential_auth_success_count']}")
    print("SECRET_VALUE_OUTPUT=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
