"""Secret-safe Docker inspection and structured diagnostic redaction.

Docker's raw inspection document is captured only inside this module and is
reduced to an allowlisted immutable record before it can reach a caller.  No
public API returns environment values, mount source paths, raw commands,
labels, exception text, or the original Docker document.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any
from urllib.parse import urlsplit, urlunsplit


REDACTED = "***"
_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|pwd|secret|token|api[_-]?key|authorization|"
    r"access[_-]?key|private[_-]?key|database[_-]?(?:url|uri)|dsn)",
    re.IGNORECASE,
)
_URI_WITH_AUTH = re.compile(
    r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<user>[^\s/:@]+):(?P<password>[^\s/@]+)@",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?P<prefix>(?:password|passwd|pwd|secret|token|api[_-]?key|"
    r"authorization|database[_-]?(?:url|uri)|dsn)\s*[:=]\s*)"
    r"(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
_SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+/-]{0,255}$")
_DATABASE_KEYS = frozenset(
    {"DATABASE_URL", "TRADERS_READONLY_API_DATABASE_URL", "TRADERS_PAPER_RUNTIME_DATABASE_URL"}
)


class SafeDockerInspectionError(RuntimeError):
    """A normalized failure whose message never contains Docker output."""


def redact_uri(value: str) -> str:
    """Redact URI userinfo passwords without ever rendering the input first."""

    return _URI_WITH_AUTH.sub(
        lambda match: f"{match.group('scheme')}{match.group('user')}:{REDACTED}@",
        value,
    )


def redact_diagnostic(value: Any, *, key: str = "") -> Any:
    """Recursively redact sensitive keys, URIs and assignment-like strings."""

    if _SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_diagnostic(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_diagnostic(item) for item in value]
    if isinstance(value, str):
        redacted = redact_uri(value)
        return _SECRET_ASSIGNMENT.sub(
            lambda match: f"{match.group('prefix')}{REDACTED}", redacted
        )
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return "<REDACTED_OBJECT>"


def _safe_identity(value: object, *, fallback: str = "UNKNOWN") -> str:
    candidate = str(value or "")
    return candidate if _SAFE_ID.fullmatch(candidate) else fallback


def _executable_identity(value: object) -> str:
    if isinstance(value, str):
        candidate = PurePath(value).name
    elif isinstance(value, Sequence) and value and isinstance(value[0], str):
        candidate = PurePath(value[0]).name
    else:
        return "NONE"
    return candidate if _SAFE_NAME.fullmatch(candidate) else "UNKNOWN"


def _env_entries(document: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    config = document.get("Config")
    if not isinstance(config, Mapping):
        return ()
    raw = config.get("Env")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    entries: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, str) or "=" not in item:
            continue
        name, value = item.split("=", 1)
        if _SAFE_NAME.fullmatch(name):
            entries.append((name, value))
    return tuple(entries)


def _principal_from_url(value: str) -> str | None:
    try:
        username = urlsplit(value.replace("postgresql+psycopg://", "postgresql://", 1)).username
    except ValueError:
        return None
    return username if username and _SAFE_NAME.fullmatch(username) else None


@dataclass(frozen=True, slots=True)
class SafeContainerInspection:
    container_name: str
    container_id: str
    image_id: str
    restart_count: int
    state: str
    health: str
    env_keys_only: tuple[str, ...]
    secret_binding_present: bool
    secret_binding_source_identity: tuple[str, ...]
    db_principals: tuple[str, ...]
    entrypoint_identity: str
    command_identity: str
    source_commit: str

    def render(self) -> str:
        fields = (
            ("container_name", self.container_name),
            ("container_id", self.container_id),
            ("image_id", self.image_id),
            ("restart_count", str(self.restart_count)),
            ("state", self.state),
            ("health", self.health),
            ("env_keys_only", ",".join(self.env_keys_only)),
            ("secret_binding_present", "YES" if self.secret_binding_present else "NO"),
            ("secret_binding_source_identity", ",".join(self.secret_binding_source_identity)),
            ("db_principals", ",".join(self.db_principals)),
            ("entrypoint_identity", self.entrypoint_identity),
            ("command_identity", self.command_identity),
            ("source_commit", self.source_commit),
        )
        return "\n".join(f"{name}={value}" for name, value in fields)


def _reduce_document(name: str, document: Mapping[str, Any]) -> SafeContainerInspection:
    state = document.get("State") if isinstance(document.get("State"), Mapping) else {}
    config = document.get("Config") if isinstance(document.get("Config"), Mapping) else {}
    entries = _env_entries(document)
    env_keys = tuple(sorted({key for key, _ in entries}))
    principals = tuple(
        sorted(
            {
                principal
                for key, value in entries
                if key in _DATABASE_KEYS
                for principal in (_principal_from_url(value),)
                if principal is not None
            }
        )
    )
    binding_identities: set[str] = set()
    mounts = document.get("Mounts")
    if isinstance(mounts, Sequence) and not isinstance(mounts, (str, bytes)):
        for mount in mounts:
            if not isinstance(mount, Mapping):
                continue
            destination = str(mount.get("Destination") or "")
            if "/run/secrets/" in destination:
                leaf = PurePath(destination).name
                if _SAFE_NAME.fullmatch(leaf):
                    binding_identities.add(f"runtime-secret:{leaf}")
    for key, _ in entries:
        if key in _DATABASE_KEYS:
            binding_identities.add(f"environment:{key}")
    labels = config.get("Labels") if isinstance(config.get("Labels"), Mapping) else {}
    revision = labels.get("org.opencontainers.image.revision", "NONE")
    health = state.get("Health") if isinstance(state.get("Health"), Mapping) else {}
    status = str(state.get("Status") or ("running" if state.get("Running") else "unknown"))
    return SafeContainerInspection(
        container_name=name if _SAFE_NAME.fullmatch(name) else "UNKNOWN",
        container_id=_safe_identity(document.get("Id")),
        image_id=_safe_identity(document.get("Image")),
        restart_count=max(0, int(document.get("RestartCount") or 0)),
        state=status if _SAFE_NAME.fullmatch(status) else "UNKNOWN",
        health=_safe_identity(health.get("Status"), fallback="NONE"),
        env_keys_only=env_keys,
        secret_binding_present=bool(binding_identities),
        secret_binding_source_identity=tuple(sorted(binding_identities)),
        db_principals=principals,
        entrypoint_identity=_executable_identity(config.get("Entrypoint")),
        command_identity=_executable_identity(config.get("Cmd")),
        source_commit=_safe_identity(revision, fallback="NONE"),
    )


def safe_inspect_container(
    name: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SafeContainerInspection:
    """Return a reduced record; raw Docker JSON never crosses this boundary."""

    if not _SAFE_NAME.fullmatch(name):
        raise SafeDockerInspectionError("INVALID_CONTAINER_IDENTITY")
    try:
        result = runner(
            ["docker", "container", "inspect", name],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode:
            raise SafeDockerInspectionError("DOCKER_INSPECTION_FAILED")
        payload = json.loads(result.stdout)
        if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], Mapping):
            raise SafeDockerInspectionError("DOCKER_INSPECTION_REJECTED")
        return _reduce_document(name, payload[0])
    except SafeDockerInspectionError:
        raise
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as error:
        raise SafeDockerInspectionError("DOCKER_INSPECTION_REJECTED") from None


__all__ = [
    "REDACTED",
    "SafeContainerInspection",
    "SafeDockerInspectionError",
    "redact_diagnostic",
    "redact_uri",
    "safe_inspect_container",
]
