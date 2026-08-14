"""Concrete, bounded adapters for production PAPER preparation.

No public method accepts or returns a credential.  The protected binding owns
generation, pending-write recovery, binding publication, and consumer probes.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import stat
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Final, Mapping, Sequence

from psycopg import sql
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.engine_paper.accounting import PaperAccountBaselineService
from app.engine_paper.baseline_repository import PaperAccountBaselineRepository

from app.engine_paper.production_preparation import (
    EXPECTED_FINAL_ALEMBIC,
    EXPECTED_PREVIOUS_ALEMBIC,
    EXPECTED_START_ALEMBIC,
    IDENTITY_KEYS,
    PRODUCTION_PAPER_RUNTIME_ROLE,
    PRODUCTION_READONLY_ROLE,
    READONLY_ACCEPTED_GRANTS,
    READONLY_BASELINE_GRANTS,
    READONLY_GRANTS,
    RUNTIME_GRANTS,
    RUNTIME_ROLE_POLICY,
    DatabaseGrant,
    classify_database_privilege_drift,
    PaperPreparationAction,
    PaperPreparationOperationResult,
    PaperProductionAccountIdentityBinding,
    PaperProductionIdentityError,
    PaperProductionTargetGuard,
)


PRODUCTION_ADMIN_PASSWORD_KEY: Final = "TRADERS_ML_POSTGRES_PASSWORD"
PRODUCTION_TARGET_ID: Final = "traders-production-primary"
PRODUCTION_PROTECTED_SOURCE: Final = Path(__file__).resolve().parents[2] / ".env.production.local"
RUNTIME_DATABASE_KEY: Final = "TRADERS_PAPER_RUNTIME_DATABASE_URL"
_ALLOWED_BINDING_KEYS: Final = frozenset({
    "DATABASE_URL", "MARKET_DATA_DATABASE_URL",
    "TRADERS_READONLY_API_DATABASE_URL", "TRADERS_READONLY_API_HOST",
    "TRADERS_READONLY_API_PORT", PRODUCTION_ADMIN_PASSWORD_KEY,
    RUNTIME_DATABASE_KEY,
})
_ENV_BINDING_KEY: Final = re.compile(r"[A-Z][A-Z0-9_]{0,127}")


class PaperPreparationAdapterError(RuntimeError):
    """Always raised with a fixed, secret-free reason code."""


READONLY_SOURCE_IDENTITY_LABEL: Final = "org.opencontainers.image.revision"
READONLY_EXPECTED_GET_ROUTES: Final = frozenset({
    "/api/v1/health", "/api/v1/dashboard", "/api/v1/markets",
    "/api/v1/markets/{symbol}", "/api/v1/analysis/{symbol}",
    "/api/v1/setups", "/api/v1/setups/{setup_id}",
    "/api/v1/incidents", "/api/v1/incidents/{incident_id}",
    "/api/v1/paper/readiness", "/api/v1/paper/account",
    "/api/v1/paper/positions", "/api/v1/paper/positions/{position_id}",
    "/api/v1/paper/trades", "/api/v1/paper/trades/{position_id}/report",
    "/api/v1/paper/reconciliation", "/api/v1/paper/runtime/status",
    "/api/v1/paper/control/status",
})
READONLY_LEGACY_ROUTES: Final = frozenset(
    path for path in READONLY_EXPECTED_GET_ROUTES if "/paper/" not in path
)
READONLY_PAPER_ROUTES: Final = READONLY_EXPECTED_GET_ROUTES - READONLY_LEGACY_ROUTES
READONLY_STATIC_PAPER_HTTP_PATHS: Final = (
    "/api/v1/paper/readiness", "/api/v1/paper/account", "/api/v1/paper/positions",
    "/api/v1/paper/trades", "/api/v1/paper/reconciliation",
    "/api/v1/paper/runtime/status", "/api/v1/paper/control/status",
)


@dataclass(frozen=True, slots=True)
class ReadonlyRuntimeAcceptance:
    """Sanitized runtime truth used by deployment and status postconditions."""

    source_identity: str
    healthy: bool
    get_routes: frozenset[str]
    write_route_count: int
    legacy_http_statuses: tuple[int, ...]
    paper_http_statuses: tuple[int, ...]

    def accepted_for(self, expected_identity: str) -> bool:
        return (
            self.source_identity == expected_identity
            and self.healthy
            and self.get_routes == READONLY_EXPECTED_GET_ROUTES
            and self.write_route_count == 0
            and len(self.legacy_http_statuses) == len(READONLY_LEGACY_ROUTES)
            and all(200 <= status < 300 for status in self.legacy_http_statuses)
            and len(self.paper_http_statuses) == len(READONLY_STATIC_PAPER_HTTP_PATHS)
            and all(status != 404 and status < 500 for status in self.paper_http_statuses)
        )


def readonly_source_identity(root: Path | None = None) -> str:
    """Hash exactly the non-secret inputs copied into the Readonly image target."""

    repository = (root or Path(__file__).resolve().parents[2]).resolve()
    fixed = (
        repository / "Dockerfile",
        repository / "requirements/api-runtime.lock.txt",
        repository / "pyproject.toml",
        repository / "README.md",
    )
    app_files = tuple(
        path for path in (repository / "app").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    )
    files = tuple(sorted((*fixed, *app_files), key=lambda path: path.relative_to(repository).as_posix()))
    if any(not path.is_file() for path in fixed):
        raise PaperPreparationAdapterError("READONLY_SOURCE_IDENTITY_UNAVAILABLE")
    digest = hashlib.sha256()
    try:
        for path in files:
            relative = path.relative_to(repository).as_posix().encode("utf-8")
            content = path.read_bytes()
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
    except Exception:
        raise PaperPreparationAdapterError("READONLY_SOURCE_IDENTITY_UNAVAILABLE") from None
    return f"sha256:{digest.hexdigest()}"


def _atomic_write(path: Path, content: str, *, template: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if template is not None and template.exists():
            os.chmod(temporary, stat.S_IMODE(template.stat().st_mode))
            if os.name == "nt":
                system_root = os.environ.get("SystemRoot", r"C:\Windows")
                powershell = Path(system_root) / "System32/WindowsPowerShell/v1.0/powershell.exe"
                completed = subprocess.run(
                    [str(powershell), "-NoProfile", "-NonInteractive", "-Command",
                     "$a=Get-Acl -LiteralPath $env:ACL_SOURCE; Set-Acl -LiteralPath $env:ACL_TARGET -AclObject $a"],
                    env={"SystemRoot": system_root, "ACL_SOURCE": str(template),
                         "ACL_TARGET": str(temporary)},
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    check=False, timeout=20,
                )
                if completed.returncode:
                    raise PaperPreparationAdapterError("PROTECTED_BINDING_SECURITY_COPY_FAILED")
        else:
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary, path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise PaperPreparationAdapterError("ATOMIC_PROTECTED_BINDING_UPDATE_FAILED") from None


def _parse_env_binding(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise PaperPreparationAdapterError("PROTECTED_BINDING_FORMAT_INVALID")
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values or key not in _ALLOWED_BINDING_KEYS:
            raise PaperPreparationAdapterError("PROTECTED_BINDING_KEYS_INVALID")
        values[key] = value
    return values


def _render_env_binding(values: Mapping[str, str]) -> str:
    ordered = (
        PRODUCTION_ADMIN_PASSWORD_KEY, "DATABASE_URL", "MARKET_DATA_DATABASE_URL",
        "TRADERS_READONLY_API_DATABASE_URL", "TRADERS_READONLY_API_HOST",
        "TRADERS_READONLY_API_PORT", RUNTIME_DATABASE_KEY,
    )
    keys = tuple(key for key in ordered if key in values)
    return "".join(f"{key}={values[key]}\n" for key in keys)


@dataclass(frozen=True, slots=True, repr=False)
class PaperProtectedBindingValidation:
    binding_present: bool
    binding_valid: bool
    consumer_configuration_ready: bool
    role_name: str = PRODUCTION_PAPER_RUNTIME_ROLE

    def __repr__(self) -> str:
        return ("PaperProtectedBindingValidation("
                f"binding_present={self.binding_present}, binding_valid={self.binding_valid}, "
                f"consumer_configuration_ready={self.consumer_configuration_ready}, "
                "role_name='traders_paper_runtime')")

    def safe_dict(self) -> dict[str, object]:
        return {"binding_present": self.binding_present, "binding_valid": self.binding_valid,
                "consumer_configuration_ready": self.consumer_configuration_ready,
                "role_name": self.role_name}


class ProtectedPaperRuntimeBindingAdapter:
    """Atomic protected file adapter with recoverable pending publication."""

    def __init__(self, binding_path: Path, admin_database_url: str | URL) -> None:
        self._path = binding_path.resolve()
        self._pending = self._path.with_name(f"{self._path.name}.pending")
        self._admin_url = admin_database_url

    def __repr__(self) -> str:
        return "ProtectedPaperRuntimeBindingAdapter(protected=True)"

    __str__ = __repr__

    def _read_values(self, path: Path) -> dict[str, str]:
        try:
            return _parse_env_binding(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except PaperPreparationAdapterError:
            raise
        except Exception:
            raise PaperPreparationAdapterError("PROTECTED_BINDING_READ_FAILED") from None

    def metadata(self) -> PaperProtectedBindingValidation:
        values = self._read_values(self._path)
        present = bool(values.get(RUNTIME_DATABASE_KEY))
        valid = False
        if present:
            try:
                url = make_url(values[RUNTIME_DATABASE_KEY])
                valid = (url.get_backend_name() == "postgresql"
                         and url.username == PRODUCTION_PAPER_RUNTIME_ROLE
                         and bool(url.password) and bool(url.database))
            except Exception:
                valid = False
        return PaperProtectedBindingValidation(present, valid, valid)

    def ensure(self, install_credential: Callable[[str], None]) -> PaperPreparationOperationResult:
        if not self._path.is_file():
            raise PaperPreparationAdapterError("PROTECTED_BINDING_FOUNDATION_MISSING")
        current = self.metadata()
        if current.binding_valid:
            return PaperPreparationOperationResult(False, True)
        pending_values = self._read_values(self._pending)
        if not pending_values.get(RUNTIME_DATABASE_KEY):
            values = self._read_values(self._path)
            credential = secrets.token_urlsafe(48)
            runtime_url = make_url(self._admin_url).set(
                username=PRODUCTION_PAPER_RUNTIME_ROLE, password=credential
            ).render_as_string(hide_password=False)
            values[RUNTIME_DATABASE_KEY] = runtime_url
            _atomic_write(self._pending, _render_env_binding(values), template=self._path)
            pending_values = values
        try:
            runtime_url = make_url(pending_values[RUNTIME_DATABASE_KEY])
            if runtime_url.username != PRODUCTION_PAPER_RUNTIME_ROLE or not runtime_url.password:
                raise PaperPreparationAdapterError("PENDING_BINDING_INVALID")
            install_credential(runtime_url.password)
            os.replace(self._pending, self._path)
            if not self.metadata().binding_valid:
                raise PaperPreparationAdapterError("PROTECTED_BINDING_POSTCONDITION_FAILED")
            return PaperPreparationOperationResult(True, True)
        except PaperPreparationAdapterError:
            raise
        except Exception:
            raise PaperPreparationAdapterError("PROTECTED_BINDING_INSTALL_FAILED") from None

    def validate_consumer(self) -> bool:
        values = self._read_values(self._path)
        runtime_url = values.get(RUNTIME_DATABASE_KEY)
        if not runtime_url or not self.metadata().binding_valid:
            return False
        engine: Engine | None = None
        try:
            engine = create_engine(runtime_url, hide_parameters=True, pool_pre_ping=True)
            with engine.connect() as connection:
                return connection.execute(text("SELECT current_user")).scalar_one() == PRODUCTION_PAPER_RUNTIME_ROLE
        except Exception:
            return False
        finally:
            if engine is not None:
                engine.dispose()


class PaperProductionIdentityConfigurationAdapter:
    """Persistent, non-secret JSON configuration with exact-key validation."""

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()

    def load(self) -> PaperProductionAccountIdentityBinding:
        def exact_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise PaperProductionIdentityError("DUPLICATE_PRODUCTION_IDENTITY_CONFIGURATION")
                result[key] = value
            return result
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"), object_pairs_hook=exact_object)
        except PaperProductionIdentityError:
            raise
        except Exception:
            raise PaperProductionIdentityError("PRODUCTION_IDENTITY_CONFIGURATION_UNAVAILABLE") from None
        if not isinstance(raw, dict) or any(not isinstance(value, str) for value in raw.values()):
            raise PaperProductionIdentityError("PRODUCTION_IDENTITY_CONFIGURATION_INVALID")
        return PaperProductionAccountIdentityBinding.from_configuration(raw)


class PaperPreparationDeploymentAdapter:
    """Builds and accepts one narrow Readonly runtime before publishing bookkeeping."""

    def __init__(self, state_root: Path, *, driver: str = "ISOLATED_FILESYSTEM",
                 compose_file: Path | None = None, compose_service: str = "readonly-api",
                 command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
                 source_identity_provider: Callable[[], str] = readonly_source_identity,
                 runtime_probe: Callable[[str], ReadonlyRuntimeAcceptance] | None = None) -> None:
        if driver not in {"ISOLATED_FILESYSTEM", "DOCKER_COMPOSE_NARROW"}:
            raise PaperPreparationAdapterError("DEPLOYMENT_DRIVER_NOT_ALLOWED")
        if compose_service != "readonly-api":
            raise PaperPreparationAdapterError("DEPLOYMENT_SERVICE_NOT_ALLOWED")
        self._root = state_root.resolve()
        self._driver = driver
        self._compose_file = compose_file.resolve() if compose_file else None
        self._service = compose_service
        self._command_runner = command_runner
        self._source_identity_provider = source_identity_provider
        self._runtime_probe = runtime_probe

    def _publish(self, name: str, payload: Mapping[str, object]) -> bool:
        path = self._root / name
        rendered = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") == rendered:
            return False
        _atomic_write(path, rendered)
        return True

    def deploy_disabled_runtime(self) -> PaperPreparationOperationResult:
        changed = self._publish("paper-runtime.disabled.json", {
            "auto_arm": False, "auto_start": False, "daemon_enabled": False,
            "dry_run": True, "live_enabled": False, "runtime_enabled": False,
            "scheduler_enabled": False, "state": "DEPLOYED_DISABLED",
        })
        return PaperPreparationOperationResult(changed, True)

    def deploy_readonly_api_narrow(self) -> PaperPreparationOperationResult:
        source_identity = self._source_identity_provider()
        if self._marker_matches(source_identity) and self._probe(source_identity).accepted_for(source_identity):
            return PaperPreparationOperationResult(False, True)
        if self._driver == "DOCKER_COMPOSE_NARROW":
            if self._compose_file is None or not self._compose_file.is_file():
                raise PaperPreparationAdapterError("READONLY_COMPOSE_UNAVAILABLE")
            environment = dict(os.environ)
            environment["TRADERS_READONLY_SOURCE_IDENTITY"] = source_identity
            built = self._command_runner(
                ["docker", "compose", "-f", str(self._compose_file), "build", self._service],
                env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=600,
            )
            if built.returncode:
                raise PaperPreparationAdapterError("READONLY_CURRENT_IMAGE_BUILD_FAILED")
            started = self._command_runner(
                ["docker", "compose", "-f", str(self._compose_file), "up", "-d",
                 "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "120", self._service],
                env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=180,
            )
            if started.returncode:
                raise PaperPreparationAdapterError("READONLY_NARROW_DEPLOYMENT_FAILED")
        acceptance = self._probe(source_identity)
        if not acceptance.accepted_for(source_identity):
            raise PaperPreparationAdapterError("READONLY_RUNTIME_ACCEPTANCE_FAILED")
        changed = self._publish("readonly-api.narrow.json", {
            "deployment": "NARROW", "service": "readonly-api", "schema": 2,
            "source_identity": source_identity, "runtime_health": "PASS",
            "get_routes": len(READONLY_EXPECTED_GET_ROUTES), "write_routes": 0,
            "legacy_endpoints": len(READONLY_LEGACY_ROUTES),
            "paper_endpoints": len(READONLY_PAPER_ROUTES),
        })
        return PaperPreparationOperationResult(changed, True)

    def accept_deployed_readonly_api_narrow(self) -> PaperPreparationOperationResult:
        """Publish bookkeeping for an already-deployed, fully accepted runtime."""

        acceptance = self._probe(self._source_identity_provider())
        runtime_identity = acceptance.source_identity
        if not acceptance.accepted_for(runtime_identity):
            raise PaperPreparationAdapterError("READONLY_RUNTIME_ACCEPTANCE_FAILED")
        changed = self._publish("readonly-api.narrow.json", {
            "deployment": "NARROW", "service": "readonly-api", "schema": 2,
            "source_identity": runtime_identity, "runtime_health": "PASS",
            "get_routes": len(READONLY_EXPECTED_GET_ROUTES), "write_routes": 0,
            "legacy_endpoints": len(READONLY_LEGACY_ROUTES),
            "paper_endpoints": len(READONLY_PAPER_ROUTES),
        })
        return PaperPreparationOperationResult(changed, True)

    def _marker_matches(self, source_identity: str) -> bool:
        path = self._root / "readonly-api.narrow.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return (
                payload.get("schema") == 2
                and payload.get("deployment") == "NARROW"
                and payload.get("service") == self._service
                and payload.get("source_identity") == source_identity
                and payload.get("runtime_health") == "PASS"
                and payload.get("get_routes") == len(READONLY_EXPECTED_GET_ROUTES)
                and payload.get("write_routes") == 0
                and payload.get("legacy_endpoints") == len(READONLY_LEGACY_ROUTES)
                and payload.get("paper_endpoints") == len(READONLY_PAPER_ROUTES)
            )
        except Exception:
            return False

    def _probe(self, expected_identity: str) -> ReadonlyRuntimeAcceptance:
        if self._runtime_probe is not None:
            return self._runtime_probe(expected_identity)
        if self._driver == "ISOLATED_FILESYSTEM":
            from app.server_api.app_factory import create_app
            document = create_app().openapi()
            routes = frozenset(
                path for path, methods in document["paths"].items() if "get" in methods
            )
            writes = sum(
                method in methods for methods in document["paths"].values()
                for method in ("post", "put", "patch", "delete")
            )
            return ReadonlyRuntimeAcceptance(
                expected_identity, True, routes, writes,
                (200,) * len(READONLY_LEGACY_ROUTES),
                (200,) * len(READONLY_STATIC_PAPER_HTTP_PATHS),
            )
        return self._probe_docker_runtime()

    def _captured(self, command: Sequence[str], reason: str, *, timeout: int = 30) -> str:
        completed = self._command_runner(
            list(command), stdin=subprocess.DEVNULL, capture_output=True, text=True,
            check=False, timeout=timeout,
        )
        if completed.returncode:
            raise PaperPreparationAdapterError(reason)
        return completed.stdout.strip()

    @staticmethod
    def _http_json(path: str) -> tuple[int, object | None]:
        request = urllib.request.Request(f"http://127.0.0.1:8765{path}", method="GET")
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw = response.read(2_000_000)
                return int(response.status), json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            error.read(2_000_000)
            return int(error.code), None
        except Exception:
            return 0, None

    @staticmethod
    def _first_identifier(payload: object, key: str) -> str | None:
        try:
            items = payload["data"]["items"]  # type: ignore[index]
            value = items[0][key]
            return value if isinstance(value, str) and value else None
        except Exception:
            return None

    def _probe_docker_runtime(self) -> ReadonlyRuntimeAcceptance:
        if self._compose_file is None:
            raise PaperPreparationAdapterError("READONLY_COMPOSE_UNAVAILABLE")
        base = ["docker", "compose", "-f", str(self._compose_file)]
        container_id = self._captured(
            [*base, "ps", "-q", self._service], "READONLY_RUNTIME_CONTAINER_UNAVAILABLE"
        )
        if not re.fullmatch(r"[a-f0-9]{12,64}", container_id):
            raise PaperPreparationAdapterError("READONLY_RUNTIME_CONTAINER_UNAVAILABLE")
        identity = self._captured(
            ["docker", "inspect", "--format",
             f'{{{{ index .Config.Labels "{READONLY_SOURCE_IDENTITY_LABEL}" }}}}', container_id],
            "READONLY_RUNTIME_IDENTITY_UNAVAILABLE",
        )
        health = self._captured(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],
            "READONLY_RUNTIME_HEALTH_UNAVAILABLE",
        )
        route_code = (
            "import json; from app.server_api.app_factory import create_app; "
            "d=create_app().openapi(); w=('post','put','patch','delete'); "
            "print(json.dumps({'get':sorted(p for p,m in d['paths'].items() if 'get' in m),"
            "'writes':sum(x in m for m in d['paths'].values() for x in w)},sort_keys=True))"
        )
        route_output = self._captured(
            [*base, "exec", "-T", self._service, "python", "-c", route_code],
            "READONLY_RUNTIME_ROUTE_DISCOVERY_FAILED",
        )
        try:
            route_payload = json.loads(route_output)
            routes = frozenset(str(path) for path in route_payload["get"])
            writes = int(route_payload["writes"])
        except Exception:
            raise PaperPreparationAdapterError("READONLY_RUNTIME_ROUTE_DISCOVERY_FAILED") from None

        legacy_statuses: list[int] = []
        for path in ("/api/v1/health", "/api/v1/dashboard", "/api/v1/markets",
                     "/api/v1/markets/BTCUSDT", "/api/v1/analysis/BTCUSDT"):
            status, _ = self._http_json(path)
            legacy_statuses.append(status)
        setups_status, setups = self._http_json("/api/v1/setups?limit=1")
        incidents_status, incidents = self._http_json("/api/v1/incidents?limit=1")
        legacy_statuses.extend((setups_status, incidents_status))
        setup_id = self._first_identifier(setups, "setup_id")
        incident_id = self._first_identifier(incidents, "incident_id")
        if setup_id is not None:
            legacy_statuses.append(self._http_json(
                "/api/v1/setups/" + urllib.parse.quote(setup_id, safe=":._-")
            )[0])
        if incident_id is not None:
            legacy_statuses.append(self._http_json(
                "/api/v1/incidents/" + urllib.parse.quote(incident_id, safe=":._-")
            )[0])
        paper_statuses = tuple(self._http_json(path)[0] for path in READONLY_STATIC_PAPER_HTTP_PATHS)
        return ReadonlyRuntimeAcceptance(
            identity, health == "healthy", routes, writes,
            tuple(legacy_statuses), paper_statuses,
        )

    def disabled_runtime_ready(self) -> bool:
        path = self._root / "paper-runtime.disabled.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return (payload.get("state") == "DEPLOYED_DISABLED"
                    and payload.get("runtime_enabled") is False
                    and payload.get("live_enabled") is False
                    and payload.get("daemon_enabled") is False
                    and payload.get("scheduler_enabled") is False)
        except Exception:
            return False

    def readonly_api_narrow_ready(self) -> bool:
        try:
            payload = json.loads((self._root / "readonly-api.narrow.json").read_text(encoding="utf-8"))
            source_identity = payload.get("source_identity")
            return (isinstance(source_identity, str)
                    and self._marker_matches(source_identity)
                    and self._probe(source_identity).accepted_for(source_identity))
        except Exception:
            return False


class PostgresPaperProductionPreparationBackend:
    """Concrete PostgreSQL 16 least-privilege preparation backend."""

    def __init__(self, engine: Engine, expected_target_id: str,
                 protected_binding: ProtectedPaperRuntimeBindingAdapter,
                 deployment: PaperPreparationDeploymentAdapter) -> None:
        self._engine = engine
        self._target_id = expected_target_id
        self._binding = protected_binding
        self._deployment = deployment

    def validate_target(self, target: PaperProductionTargetGuard) -> bool:
        if target.database_target_id != self._target_id:
            return False
        try:
            with self._engine.connect() as connection:
                major = int(connection.execute(text("SHOW server_version_num")).scalar_one()) // 10000
                revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            return major == 16 and revision == target.expected_start_alembic
        except Exception:
            return False

    def current_revision(self) -> str:
        try:
            with self._engine.connect() as connection:
                return str(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())
        except Exception:
            raise PaperPreparationAdapterError("SCHEMA_REVISION_UNAVAILABLE") from None

    def migrate_to_final(self) -> PaperPreparationOperationResult:
        from app.engine_paper.production_preparation import EXPECTED_FINAL_ALEMBIC
        if self.current_revision() == EXPECTED_FINAL_ALEMBIC:
            return PaperPreparationOperationResult(False, True)
        if self.current_revision() not in {EXPECTED_START_ALEMBIC, EXPECTED_PREVIOUS_ALEMBIC}:
            raise PaperPreparationAdapterError("SCHEMA_REVISION_MISMATCH")
        import app.config.settings as settings
        original = settings.get_settings
        settings.get_settings = lambda: type("PreparationSettings", (), {
            "database_url": self._engine.url.render_as_string(hide_password=False)
        })()
        try:
            command.upgrade(Config("alembic.ini"), EXPECTED_FINAL_ALEMBIC)
        finally:
            settings.get_settings = original
        if self.current_revision() != EXPECTED_FINAL_ALEMBIC:
            raise PaperPreparationAdapterError("SCHEMA_MIGRATION_POSTCONDITION_FAILED")
        return PaperPreparationOperationResult(True, True)

    def ensure_baseline(self, identity: PaperProductionAccountIdentityBinding,
                        initial_balance: Decimal) -> PaperPreparationOperationResult:
        if initial_balance != Decimal("100.00"):
            raise PaperPreparationAdapterError("BASELINE_BUDGET_MISMATCH")
        account = identity.account_identity()
        factory = sessionmaker(bind=self._engine, autoflush=False, expire_on_commit=False)
        with factory.begin() as session:
            repository = PaperAccountBaselineRepository(session)
            existed = repository.exists(account.account_id, account.accounting_session_id)
            PaperAccountBaselineService(repository).initialize(
                baseline_id="baseline:production-paper-v1", identity=account,
                initial_balance=initial_balance, initialized_at=datetime.now(timezone.utc))
        return PaperPreparationOperationResult(not existed, True)

    def _role_row(self, role: str):
        with self._engine.connect() as connection:
            return connection.execute(text(
                "SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
                "FROM pg_roles WHERE rolname=:role"), {"role": role}).one_or_none()

    def _extra_privileges(self, role: str, grants: tuple[DatabaseGrant, ...]) -> bool:
        with self._engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT table_name,privilege_type,is_grantable FROM information_schema.role_table_grants "
                "WHERE grantee=:role AND table_schema='public'"), {"role": role}).all()
            memberships = connection.execute(text(
                "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=:role"),
                {"role": role}).scalar_one()
            ownership = connection.execute(text(
                "SELECT (SELECT count(*) FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname=:role) + "
                "(SELECT count(*) FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE r.rolname=:role) + "
                "(SELECT count(*) FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner WHERE r.rolname=:role) + "
                "(SELECT count(*) FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE r.rolname=:role)"),
                {"role": role}).scalar_one()
            non_table_acl = connection.execute(text(
                "SELECT count(*) FROM ("
                " SELECT x.privilege_type FROM pg_namespace n CROSS JOIN LATERAL aclexplode(n.nspacl) x"
                " JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname=:role"
                " AND (n.nspname<>'public' OR x.privilege_type<>'USAGE' OR x.is_grantable)"
                " UNION ALL SELECT x.privilege_type FROM pg_database d CROSS JOIN LATERAL aclexplode(d.datacl) x"
                " JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname=:role"
                " AND (d.datname<>current_database() OR x.privilege_type<>'CONNECT' OR x.is_grantable)"
                " UNION ALL SELECT x.privilege_type FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) x"
                " JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname=:role"
                " UNION ALL SELECT x.privilege_type FROM pg_class c CROSS JOIN LATERAL aclexplode(c.relacl) x"
                " JOIN pg_roles r ON r.oid=x.grantee WHERE r.rolname=:role AND c.relkind='S'"
                ") unexpected"), {"role": role}).scalar_one()
        return classify_database_privilege_drift(
            tuple((str(table_name), str(privilege), str(grantable))
                  for table_name, privilege, grantable in rows),
            grants, memberships=int(memberships), ownership=int(ownership),
            non_table_acl=int(non_table_acl),
        )

    def _required_privileges(self, role: str, grants: tuple[DatabaseGrant, ...]) -> bool:
        if self._role_row(role) is None:
            return False
        try:
            with self._engine.connect() as connection:
                return all(connection.execute(text(
                    "SELECT has_table_privilege(:role,:table,:operation)"), {
                        "role": role, "table": f"public.{grant.table}", "operation": operation,
                    }).scalar_one() for grant in grants for operation in grant.operations)
        except Exception:
            return False

    def inspect_runtime_role(self) -> str:
        row = self._role_row(PRODUCTION_PAPER_RUNTIME_ROLE)
        if row is None:
            return "ABSENT"
        if tuple(row) != (True, False, False, False, False, False):
            return "BROADER_THAN_CONTRACT"
        return "BROADER_THAN_CONTRACT" if self._extra_privileges(PRODUCTION_PAPER_RUNTIME_ROLE, RUNTIME_GRANTS) else "EXACT_OR_NARROWER"

    def inspect_privilege_drift(self) -> bool:
        runtime = self.inspect_runtime_role()
        if runtime == "BROADER_THAN_CONTRACT":
            return True
        readonly = self._role_row(PRODUCTION_READONLY_ROLE)
        return bool(readonly is not None and (
            any(readonly[1:]) or self._extra_privileges(PRODUCTION_READONLY_ROLE, READONLY_ACCEPTED_GRANTS)
        ))

    def ensure_runtime_role(self) -> PaperPreparationOperationResult:
        state = self.inspect_runtime_role()
        if state == "BROADER_THAN_CONTRACT":
            raise PaperPreparationAdapterError("EXISTING_ROLE_PRIVILEGE_DRIFT")
        if state != "ABSENT":
            return PaperPreparationOperationResult(False, True)
        with self._engine.begin() as connection:
            connection.exec_driver_sql(
                f'CREATE ROLE "{PRODUCTION_PAPER_RUNTIME_ROLE}" LOGIN NOSUPERUSER NOCREATEDB '
                'NOCREATEROLE NOREPLICATION NOBYPASSRLS')
        if self._role_row(PRODUCTION_PAPER_RUNTIME_ROLE) is None:
            raise PaperPreparationAdapterError("RUNTIME_ROLE_POSTCONDITION_FAILED")
        return PaperPreparationOperationResult(True, True)

    def _install_password(self, password: str) -> None:
        raw = self._engine.raw_connection()
        try:
            with raw.cursor() as cursor:
                cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(PRODUCTION_PAPER_RUNTIME_ROLE), sql.Literal(password)))
            raw.commit()
        except Exception:
            raw.rollback()
            raise
        finally:
            raw.close()

    def ensure_runtime_binding(self) -> PaperPreparationOperationResult:
        if self._role_row(PRODUCTION_PAPER_RUNTIME_ROLE) is None:
            raise PaperPreparationAdapterError("RUNTIME_ROLE_REQUIRED_BEFORE_BINDING")
        return self._binding.ensure(self._install_password)

    def validate_runtime_binding(self) -> bool:
        return self._binding.validate_consumer()

    def _reconcile(self, role: str, grants: tuple[DatabaseGrant, ...]) -> PaperPreparationOperationResult:
        row = self._role_row(role)
        if row is None:
            raise PaperPreparationAdapterError("REQUIRED_DATABASE_ROLE_MISSING")
        accepted = READONLY_ACCEPTED_GRANTS if role == PRODUCTION_READONLY_ROLE else grants
        if any(row[1:]) or self._extra_privileges(role, accepted):
            raise PaperPreparationAdapterError("EXISTING_ROLE_PRIVILEGE_DRIFT")
        changed = False
        with self._engine.begin() as connection:
            for grant in grants:
                missing = [operation for operation in grant.operations if not connection.execute(text(
                    "SELECT has_table_privilege(:role,:table,:operation)"),
                    {"role": role, "table": f"public.{grant.table}", "operation": operation}).scalar_one()]
                if missing:
                    operations = ", ".join(missing)
                    connection.exec_driver_sql(f'GRANT {operations} ON TABLE "{grant.table}" TO "{role}"')
                    changed = True
        if self._extra_privileges(role, accepted):
            raise PaperPreparationAdapterError("GRANT_POSTCONDITION_FAILED")
        with self._engine.connect() as connection:
            if any(not connection.execute(text("SELECT has_table_privilege(:role,:table,:operation)"),
                    {"role": role, "table": f"public.{grant.table}", "operation": operation}).scalar_one()
                   for grant in grants for operation in grant.operations):
                raise PaperPreparationAdapterError("GRANT_POSTCONDITION_FAILED")
        return PaperPreparationOperationResult(changed, True)

    def reconcile_runtime_grants(self) -> PaperPreparationOperationResult:
        return self._reconcile(PRODUCTION_PAPER_RUNTIME_ROLE, RUNTIME_GRANTS)

    def reconcile_readonly_grants(self) -> PaperPreparationOperationResult:
        return self._reconcile(PRODUCTION_READONLY_ROLE, READONLY_GRANTS)

    def baseline_ready(self, identity: PaperProductionAccountIdentityBinding) -> bool:
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(text(
                    "SELECT account_id,accounting_session_id,currency,initial_balance "
                    "FROM paper_account_baselines"
                )).all()
            return len(rows) == 1 and tuple(rows[0]) == (
                identity.paper_account_id, identity.accounting_session_id,
                identity.currency, Decimal("100.00"),
            )
        except Exception:
            return False

    def action_satisfied(self, action: PaperPreparationAction) -> bool:
        if action is PaperPreparationAction.ENSURE_RUNTIME_ROLE:
            return self.inspect_runtime_role() == "EXACT_OR_NARROWER"
        if action is PaperPreparationAction.APPLY_RUNTIME_GRANTS:
            return (self.inspect_runtime_role() == "EXACT_OR_NARROWER"
                    and self._required_privileges(PRODUCTION_PAPER_RUNTIME_ROLE, RUNTIME_GRANTS))
        if action is PaperPreparationAction.APPLY_READONLY_REPORTING_GRANTS:
            return (not self.inspect_privilege_drift()
                    and self._required_privileges(PRODUCTION_READONLY_ROLE, READONLY_GRANTS))
        if action is PaperPreparationAction.BIND_RUNTIME_CREDENTIAL:
            return self._binding.metadata().binding_valid
        if action is PaperPreparationAction.VALIDATE_RUNTIME_BINDING:
            return self._binding.validate_consumer()
        if action is PaperPreparationAction.DEPLOY_DISABLED_RUNTIME_CONFIGURATION:
            return self._deployment.disabled_runtime_ready()
        if action is PaperPreparationAction.DEPLOY_READONLY_API_NARROW:
            return self._deployment.readonly_api_narrow_ready()
        return False

    def preparation_state(self, identity: PaperProductionAccountIdentityBinding):
        from app.engine_paper.production_preparation import (
            PaperProductionPreparationState, classify_preparation_phase,
        )
        revision = self.current_revision()
        drift = self.inspect_privilege_drift()
        runtime_role_ready = self.action_satisfied(PaperPreparationAction.ENSURE_RUNTIME_ROLE)
        runtime_grants_ready = self.action_satisfied(PaperPreparationAction.APPLY_RUNTIME_GRANTS)
        readonly_ready = self.action_satisfied(PaperPreparationAction.APPLY_READONLY_REPORTING_GRANTS)
        readonly_baseline_ready = self._required_privileges(
            PRODUCTION_READONLY_ROLE, READONLY_BASELINE_GRANTS,
        )
        binding_ready = self._binding.validate_consumer() if self._binding.metadata().binding_valid else False
        runtime_config_ready = self._deployment.disabled_runtime_ready()
        readonly_deployed = self._deployment.readonly_api_narrow_ready()
        baseline_ready = self.baseline_ready(identity) if revision == EXPECTED_FINAL_ALEMBIC else False
        complete = all((runtime_role_ready, runtime_grants_ready, readonly_ready, binding_ready,
                        runtime_config_ready, readonly_deployed, baseline_ready))
        phase = classify_preparation_phase(
            revision, preparation_complete=complete, privilege_drift=drift,
            incompatible_postcondition=not readonly_baseline_ready,
        )
        return PaperProductionPreparationState(
            revision, phase, revision == EXPECTED_FINAL_ALEMBIC, baseline_ready,
            binding_ready, runtime_role_ready, runtime_grants_ready, readonly_ready,
            readonly_baseline_ready, runtime_config_ready, readonly_deployed, drift,
        )

    def safe_invariance_counts(self) -> dict[str, int | None]:
        """Return only fixed bounded production invariance counters."""
        tables = {
            "baseline_count": "paper_account_baselines",
            "paper_commands": "paper_execution_commands",
            "paper_orders": "paper_orders",
            "paper_fills": "paper_fills",
            "paper_positions": "paper_positions",
            "paper_canaries": "paper_first_canary_sessions",
        }
        result: dict[str, int | None] = {}
        with self._engine.connect() as connection:
            result["schema_head_count"] = int(connection.execute(text(
                "SELECT count(*) FROM alembic_version"
            )).scalar_one())
            for key, table_name in tables.items():
                try:
                    result[key] = int(connection.execute(text(
                        f'SELECT count(*) FROM "{table_name}"'
                    )).scalar_one())
                except Exception:
                    connection.rollback()
                    result[key] = None
        return result

    def deploy_disabled_runtime(self) -> PaperPreparationOperationResult:
        return self._deployment.deploy_disabled_runtime()

    def deploy_readonly_api_narrow(self) -> PaperPreparationOperationResult:
        return self._deployment.deploy_readonly_api_narrow()


class PaperProductionPreparationTargetBinding:
    """Opaque production administrator capability and target binding.

    The protected value is retained only long enough to construct an engine.
    Public methods return composed dependencies or fixed, non-secret failures;
    no raw protected value or credential-bearing URL crosses this boundary.
    """

    def __init__(
        self,
        protected_source: Path,
        target_id: str,
        *,
        admin_host: str = "127.0.0.1",
        admin_port: int = 5433,
        admin_database: str = "traders_ml",
        admin_user: str = "traders_ml",
        protected_value_provider: Callable[[Path], str] | None = None,
        engine_factory: Callable[..., Engine] = create_engine,
    ) -> None:
        self._source = protected_source.resolve()
        self._target_id = target_id
        self._admin_host = admin_host
        self._admin_port = admin_port
        self._admin_database = admin_database
        self._admin_user = admin_user
        self._value_provider = protected_value_provider or self._read_admin_password
        self._engine_factory = engine_factory

    def __repr__(self) -> str:
        return "PaperProductionPreparationTargetBinding(protected=True)"

    __str__ = __repr__

    @staticmethod
    def _read_admin_password(path: Path) -> str:
        """Read exactly one protected capability without retaining other values."""
        found: str | None = None
        try:
            with path.open("r", encoding="utf-8") as stream:
                for raw in stream:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    key, separator, value = line.partition("=")
                    key = key.strip()
                    if not separator or not _ENV_BINDING_KEY.fullmatch(key):
                        raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_INVALID")
                    if key == PRODUCTION_ADMIN_PASSWORD_KEY:
                        if found is not None or not value:
                            raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_INVALID")
                        found = value
        except PaperPreparationAdapterError:
            raise
        except Exception:
            raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_UNAVAILABLE") from None
        if found is None:
            raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_UNAVAILABLE")
        return found

    def build_engine(self) -> Engine:
        if (not self._target_id or self._admin_host != "127.0.0.1"
                or not isinstance(self._admin_port, int) or not 1 <= self._admin_port <= 65535
                or not self._admin_database or not self._admin_user):
            raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_INVALID")
        try:
            PaperProductionTargetGuard(database_target_id=self._target_id)
            password = self._value_provider(self._source)
            if not isinstance(password, str) or not password:
                raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_INVALID")
            url = URL.create(
                "postgresql+psycopg",
                username=self._admin_user,
                password=password,
                host=self._admin_host,
                port=self._admin_port,
                database=self._admin_database,
            )
            return self._engine_factory(url, hide_parameters=True, pool_pre_ping=True)
        except PaperPreparationAdapterError:
            raise
        except Exception:
            raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_INVALID") from None


@dataclass(frozen=True, slots=True)
class PaperProductionPreparationComposition:
    executor: object
    backend: PostgresPaperProductionPreparationBackend
    protected_binding: ProtectedPaperRuntimeBindingAdapter
    identity: PaperProductionAccountIdentityBinding
    target: PaperProductionTargetGuard
    target_binding: PaperProductionPreparationTargetBinding


def compose_production_preparation(
    config: Mapping[str, object],
    *,
    production_mode: bool = False,
    protected_value_provider: Callable[[Path], str] | None = None,
    engine_factory: Callable[..., Engine] = create_engine,
):
    """Build the real executor through one opaque, secret-free target binding."""
    from app.engine_paper.production_preparation import PaperProductionPreparationExecutor
    validate_production_preparation_config(config)
    target_id = str(config["target_id"])
    protected_source = Path(str(config["protected_binding"])).resolve()
    if production_mode:
        if target_id != PRODUCTION_TARGET_ID:
            raise PaperPreparationAdapterError("PRODUCTION_TARGET_MISMATCH")
        if (protected_source != PRODUCTION_PROTECTED_SOURCE
                or config["deployment_driver"] != "DOCKER_COMPOSE_NARROW"
                or config.get("admin_host", "127.0.0.1") != "127.0.0.1"
                or config.get("admin_port", 5433) != 5433
                or config.get("admin_database", "traders_ml") != "traders_ml"
                or config.get("admin_user", "traders_ml") != "traders_ml"):
            raise PaperPreparationAdapterError("PRODUCTION_TARGET_BINDING_INVALID")
    elif target_id == PRODUCTION_TARGET_ID:
        raise PaperPreparationAdapterError("PRODUCTION_TARGET_MISMATCH")
    target_binding = PaperProductionPreparationTargetBinding(
        protected_source, target_id,
        admin_host=str(config.get("admin_host", "127.0.0.1")),
        admin_port=int(config.get("admin_port", 5433)),
        admin_database=str(config.get("admin_database", "traders_ml")),
        admin_user=str(config.get("admin_user", "traders_ml")),
        protected_value_provider=protected_value_provider,
        engine_factory=engine_factory,
    )
    engine = target_binding.build_engine()
    identity = PaperProductionIdentityConfigurationAdapter(Path(str(config["identity_config"]))).load()
    binding = ProtectedPaperRuntimeBindingAdapter(protected_source, engine.url)
    deployment = PaperPreparationDeploymentAdapter(
        Path(str(config["state_root"])), driver=str(config["deployment_driver"]),
        compose_file=(Path(str(config["compose_file"])) if config.get("compose_file") else None),
    )
    backend = PostgresPaperProductionPreparationBackend(engine, target_id, binding, deployment)
    target = PaperProductionTargetGuard(database_target_id=target_id)
    return PaperProductionPreparationComposition(
        PaperProductionPreparationExecutor(backend), backend, binding, identity, target, target_binding)


def validate_production_preparation_config(config: Mapping[str, object]) -> None:
    """Validate only non-secret composition shape; safe for plan mode."""
    required = {"identity_config", "protected_binding", "state_root", "target_id", "deployment_driver"}
    optional = {"compose_file", "admin_host", "admin_port", "admin_database", "admin_user"}
    if set(config) - (required | optional) or not required <= set(config):
        raise PaperPreparationAdapterError("PRODUCTION_COMPOSITION_CONFIGURATION_INVALID")
    if any(not isinstance(config[key], str) or not config[key] for key in required):
        raise PaperPreparationAdapterError("PRODUCTION_COMPOSITION_CONFIGURATION_INVALID")
    if any(key in config and (not isinstance(config[key], str) or not config[key])
           for key in ("admin_host", "admin_database", "admin_user")):
        raise PaperPreparationAdapterError("PRODUCTION_COMPOSITION_CONFIGURATION_INVALID")
    if "admin_port" in config and (not isinstance(config["admin_port"], int)
                                    or not 1 <= config["admin_port"] <= 65535):
        raise PaperPreparationAdapterError("PRODUCTION_COMPOSITION_CONFIGURATION_INVALID")
    PaperProductionTargetGuard(database_target_id=str(config["target_id"]))
    if config["deployment_driver"] not in {"ISOLATED_FILESYSTEM", "DOCKER_COMPOSE_NARROW"}:
        raise PaperPreparationAdapterError("DEPLOYMENT_DRIVER_NOT_ALLOWED")
    if config["deployment_driver"] == "DOCKER_COMPOSE_NARROW" and not config.get("compose_file"):
        raise PaperPreparationAdapterError("READONLY_COMPOSE_UNAVAILABLE")


__all__ = [name for name in globals() if name.startswith("Paper") or name.startswith("Postgres") or name in {
    "PRODUCTION_ADMIN_PASSWORD_KEY", "PRODUCTION_PROTECTED_SOURCE", "PRODUCTION_TARGET_ID",
    "RUNTIME_DATABASE_KEY",
    "compose_production_preparation",
    "validate_production_preparation_config",
}]
