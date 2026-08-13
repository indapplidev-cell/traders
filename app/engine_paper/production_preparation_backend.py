"""Concrete, bounded adapters for production PAPER preparation.

No public method accepts or returns a credential.  The protected binding owns
generation, pending-write recovery, binding publication, and consumer probes.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Final, Mapping

from psycopg import sql
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from app.engine_paper.accounting import PaperAccountBaselineService
from app.engine_paper.baseline_repository import PaperAccountBaselineRepository

from app.engine_paper.production_preparation import (
    EXPECTED_START_ALEMBIC,
    IDENTITY_KEYS,
    PRODUCTION_PAPER_RUNTIME_ROLE,
    PRODUCTION_READONLY_ROLE,
    READONLY_GRANTS,
    RUNTIME_GRANTS,
    RUNTIME_ROLE_POLICY,
    DatabaseGrant,
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
    """Publishes disabled runtime state and optionally performs one narrow deploy."""

    def __init__(self, state_root: Path, *, driver: str = "ISOLATED_FILESYSTEM",
                 compose_file: Path | None = None, compose_service: str = "readonly-api") -> None:
        if driver not in {"ISOLATED_FILESYSTEM", "DOCKER_COMPOSE_NARROW"}:
            raise PaperPreparationAdapterError("DEPLOYMENT_DRIVER_NOT_ALLOWED")
        if compose_service != "readonly-api":
            raise PaperPreparationAdapterError("DEPLOYMENT_SERVICE_NOT_ALLOWED")
        self._root = state_root.resolve()
        self._driver = driver
        self._compose_file = compose_file.resolve() if compose_file else None
        self._service = compose_service

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
        if self._driver == "DOCKER_COMPOSE_NARROW":
            if self._compose_file is None or not self._compose_file.is_file():
                raise PaperPreparationAdapterError("READONLY_COMPOSE_UNAVAILABLE")
            completed = subprocess.run(
                ["docker", "compose", "-f", str(self._compose_file), "up", "-d", "--no-deps", self._service],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=False, timeout=180,
            )
            if completed.returncode:
                raise PaperPreparationAdapterError("READONLY_NARROW_DEPLOYMENT_FAILED")
        changed = self._publish("readonly-api.narrow.json", {
            "deployment": "NARROW", "service": "readonly-api", "write_routes": 0,
        })
        return PaperPreparationOperationResult(changed, True)


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
        if self.current_revision() != EXPECTED_START_ALEMBIC:
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
        expected = {(item.table, operation) for item in grants for operation in item.operations}
        with self._engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT table_name,privilege_type,is_grantable FROM information_schema.role_table_grants "
                "WHERE grantee=:role AND table_schema='public'"), {"role": role}).all()
            memberships = connection.execute(text(
                "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=:role"),
                {"role": role}).scalar_one()
            ownership = connection.execute(text(
                "SELECT (SELECT count(*) FROM pg_database d JOIN pg_roles r ON r.oid=d.datdba WHERE r.rolname=:role) + "
                "(SELECT count(*) FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner WHERE r.rolname=:role)"),
                {"role": role}).scalar_one()
        return bool(memberships or ownership or any(
            grantable == "YES" or (table_name, privilege) not in expected
            for table_name, privilege, grantable in rows
        ))

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
            any(readonly[1:]) or self._extra_privileges(PRODUCTION_READONLY_ROLE, READONLY_GRANTS)
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
        if any(row[1:]) or self._extra_privileges(role, grants):
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
        if self._extra_privileges(role, grants):
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
