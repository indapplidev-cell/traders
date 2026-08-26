"""Fail-closed, no-echo controls for tracked secret incident remediation.

The public objects in this module return only fixed classifications and
structural metadata.  They never return source values, environment values,
connection strings, exception messages, raw lines, or deterministic secret
derivatives.
"""

from __future__ import annotations

import ast
import re
import secrets
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlsplit
from urllib.request import urlopen

from app.db.postgres_auth_probe import PostgresAuthenticationProbe


PROTECTED_BINDING_NAME = ".env.production.local"
POSTGRES_PASSWORD_KEY_PATH = "services.postgres.environment.POSTGRES_PASSWORD_FILE"
POSTGRES_PASSWORD_REFERENCE_KEY = "TRADERS_ML_POSTGRES_PASSWORD"
_APPROVED_SHARED_DB_SECRET_REFERENCES = {
    (
        "services.postgres.environment.POSTGRES_PASSWORD_FILE",
        "/run/secrets/traders_shared_db_password",
    ),
    (
        "secrets.traders_shared_db_password.file",
        "./.secrets.production.local/shared-db-password",
    ),
    (
        "services.operator-control-api.environment.TRADERS_ML_POSTGRES_PASSWORD",
        "",
    ),
    (
        "services.operator-control-api.secrets.[]",
        "traders_control_api_token",
    ),
    (
        "secrets.traders_control_api_token.file",
        "../../../.control-api.token",
    ),
    *(
        (f"services.{service}.secrets.[]", "traders_shared_db_password")
        for service in (
            "postgres",
            "market-data-sync",
            "online-orchestrator",
            "online-orchestrator-5m",
            "scalping-calibration-collector",
        )
    ),
}
_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
)
_REQUIRED_REFERENCE = re.compile(
    r"^\$\{(?P<name>[A-Z_][A-Z0-9_]*)(?::\?|[?])[^}]*\}$"
)
_ANY_REFERENCE = re.compile(r"^\$\{[A-Z_][A-Z0-9_]*(?P<operator>[^A-Z0-9_}]+)?[^}]*\}$")
_CREDENTIAL_URL = re.compile(
    r"^[a-z][a-z0-9+.-]*://[^/@:\s]+:[^/@\s]+@",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?:^|[\s,;])(?:password|passwd|pwd|secret|token|api[_-]?key|"
    r"access[_-]?key|private[_-]?key)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
_SAFE_PLACEHOLDERS = {
    "changeme",
    "example",
    "placeholder",
    "replace_me",
    "not-a-real-secret",
}


class ValueClass(StrEnum):
    REQUIRED_ENV_REFERENCE = "REQUIRED_ENV_REFERENCE"
    ENV_REFERENCE_WITH_DEFAULT = "ENV_REFERENCE_WITH_DEFAULT"
    ENV_REFERENCE_NOT_REQUIRED = "ENV_REFERENCE_NOT_REQUIRED"
    APPROVED_EXTERNAL_SECRET_REFERENCE = "APPROVED_EXTERNAL_SECRET_REFERENCE"
    SAFE_EXAMPLE_PLACEHOLDER = "SAFE_EXAMPLE_PLACEHOLDER"
    LITERAL_SECRET = "LITERAL_SECRET"
    CREDENTIAL_BEARING_URL = "CREDENTIAL_BEARING_URL"
    NON_SECRET = "NON_SECRET"
    MISSING = "MISSING"
    PARSE_ERROR = "PARSE_ERROR"


class PolicyResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class SafeParserError:
    file: str
    document_index: int
    key_path: str
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"file={self.file}",
                f"document_index={self.document_index}",
                f"key_path={self.key_path}",
                f"error_class={self.error_class}",
            )
        )


@dataclass(frozen=True, slots=True)
class TrackedValue:
    file: str
    document_index: int
    key_path: str
    value_class: ValueClass
    policy_result: PolicyResult

    def render(self) -> str:
        return "\n".join(
            (
                f"file={self.file}",
                f"key_path={self.key_path}",
                f"value_class={self.value_class.value}",
                f"policy_result={self.policy_result.value}",
            )
        )


@dataclass(frozen=True, slots=True)
class SafeTrackedFileInspection:
    file: str
    file_exists: bool
    key_exists: bool
    value_class: ValueClass
    policy_result: PolicyResult
    parser_error: SafeParserError | None = None

    def render(self) -> str:
        lines = (
            f"file={self.file}",
            f"file_exists={'YES' if self.file_exists else 'NO'}",
            f"key_exists={'YES' if self.key_exists else 'NO'}",
            f"value_class={self.value_class.value}",
            f"policy_result={self.policy_result.value}",
        )
        if self.parser_error is None:
            return "\n".join(lines)
        return "\n".join((*lines, self.parser_error.render()))


@dataclass(frozen=True, slots=True)
class ParsedScalar:
    document_index: int
    key_path: str
    value: str


@dataclass(frozen=True, slots=True)
class SafeYamlParse:
    scalars: tuple[ParsedScalar, ...]
    errors: tuple[SafeParserError, ...]


def _safe_file_name(path: Path | str) -> str:
    return Path(path).name


def _strip_scalar_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_indented_yaml_scalars(
    text: str,
    *,
    file: str,
) -> SafeYamlParse:
    """Parse simple Compose mapping scalars without retaining raw lines.

    Unsupported YAML constructs fail closed with typed metadata.  Values remain
    private to the returned structural object and are never part of renderers.
    """

    scalars: list[ParsedScalar] = []
    errors: list[SafeParserError] = []
    stack: list[tuple[int, str]] = []
    document_index = 0
    block_indent: int | None = None
    block_path = ""
    block_document_index = 0
    block_parts: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))
        if block_indent is not None:
            if not stripped or indent > block_indent:
                if stripped:
                    block_parts.append(stripped)
                continue
            scalars.append(
                ParsedScalar(
                    block_document_index,
                    block_path,
                    "\n".join(block_parts),
                )
            )
            block_indent = None
            block_path = ""
            block_parts = []
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "---":
            document_index += 1
            stack.clear()
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            errors.append(
                SafeParserError(file, document_index, "", "TAB_INDENTATION")
            )
            continue
        if indent % 2:
            errors.append(
                SafeParserError(file, document_index, "", "ODD_INDENTATION")
            )
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if "=" not in item:
                path = ".".join((*[key for _, key in stack], "[]"))
                scalars.append(
                    ParsedScalar(
                        document_index,
                        path,
                        _strip_scalar_quotes(item),
                    )
                )
                continue
            key, value = item.split("=", 1)
            key = key.strip()
            if not key:
                errors.append(
                    SafeParserError(
                        file,
                        document_index,
                        ".".join(key for _, key in stack),
                        "EMPTY_SEQUENCE_KEY",
                    )
                )
                continue
            path = ".".join((*[part for _, part in stack], key))
            scalars.append(
                ParsedScalar(document_index, path, _strip_scalar_quotes(value.strip()))
            )
            continue

        key, separator, value = stripped.partition(":")
        key = key.strip().strip("'\"")
        if not separator or not key:
            errors.append(
                SafeParserError(
                    file,
                    document_index,
                    ".".join(part for _, part in stack),
                    "MALFORMED_MAPPING",
                )
            )
            continue
        path = ".".join((*[part for _, part in stack], key))
        value = value.strip()
        if not value:
            stack.append((indent, key))
            continue
        if value in {"|", ">"}:
            block_indent = indent
            block_path = path
            block_document_index = document_index
            block_parts = []
            continue
        scalars.append(
            ParsedScalar(document_index, path, _strip_scalar_quotes(value))
        )
    if block_indent is not None:
        scalars.append(
            ParsedScalar(
                block_document_index,
                block_path,
                "\n".join(block_parts),
            )
        )
    return SafeYamlParse(tuple(scalars), tuple(errors))


def _is_sensitive_key(key_path: str) -> bool:
    normalized = key_path.casefold().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def classify_tracked_value(
    key_path: str,
    value: str,
    *,
    example_file: bool = False,
) -> ValueClass:
    if (key_path, value) in _APPROVED_SHARED_DB_SECRET_REFERENCES:
        return ValueClass.APPROVED_EXTERNAL_SECRET_REFERENCE
    if _CREDENTIAL_URL.match(value):
        return ValueClass.CREDENTIAL_BEARING_URL
    if _SECRET_ASSIGNMENT.search(value):
        return ValueClass.LITERAL_SECRET
    security_relevant = _is_sensitive_key(key_path) or key_path.casefold().endswith(
        ("database_url", "credential_url", "connection_url")
    )
    required = _REQUIRED_REFERENCE.match(value)
    if required:
        return (
            ValueClass.REQUIRED_ENV_REFERENCE
            if security_relevant
            else ValueClass.NON_SECRET
        )
    reference = _ANY_REFERENCE.match(value)
    if reference:
        if not security_relevant:
            return ValueClass.NON_SECRET
        operator = reference.group("operator") or ""
        if ":-" in operator or "-" in operator or ":=" in operator or "=" in operator:
            return ValueClass.ENV_REFERENCE_WITH_DEFAULT
        return ValueClass.ENV_REFERENCE_NOT_REQUIRED
    if key_path.casefold().endswith((".secret.file", ".secrets.external")):
        return ValueClass.APPROVED_EXTERNAL_SECRET_REFERENCE
    if _is_sensitive_key(key_path):
        if example_file and value.casefold() in _SAFE_PLACEHOLDERS:
            return ValueClass.SAFE_EXAMPLE_PLACEHOLDER
        return ValueClass.LITERAL_SECRET
    return ValueClass.NON_SECRET


def tracked_compose_policy(
    path: Path,
    *,
    text_reader: Callable[[Path], str] | None = None,
) -> tuple[TrackedValue, ...] | tuple[SafeParserError, ...]:
    reader = text_reader or (lambda item: item.read_text(encoding="utf-8"))
    file = _safe_file_name(path)
    try:
        parsed = parse_indented_yaml_scalars(reader(path), file=file)
    except (OSError, UnicodeError):
        return (SafeParserError(file, 0, "", "SAFE_READ_FAILED"),)
    if parsed.errors:
        return parsed.errors
    findings: list[TrackedValue] = []
    example_file = ".example." in path.name.casefold()
    for scalar in parsed.scalars:
        value_class = classify_tracked_value(
            scalar.key_path,
            scalar.value,
            example_file=example_file,
        )
        if value_class is ValueClass.NON_SECRET:
            continue
        allowed = value_class in {
            ValueClass.REQUIRED_ENV_REFERENCE,
            ValueClass.APPROVED_EXTERNAL_SECRET_REFERENCE,
            ValueClass.SAFE_EXAMPLE_PLACEHOLDER,
        }
        findings.append(
            TrackedValue(
                file=file,
                document_index=scalar.document_index,
                key_path=scalar.key_path,
                value_class=value_class,
                policy_result=PolicyResult.PASS if allowed else PolicyResult.FAIL,
            )
        )
    return tuple(findings)


def inspect_tracked_compose_key(
    path: Path,
    key_path: str,
    *,
    text_reader: Callable[[Path], str] | None = None,
) -> SafeTrackedFileInspection:
    file = _safe_file_name(path)
    if not path.is_file() and text_reader is None:
        return SafeTrackedFileInspection(
            file, False, False, ValueClass.MISSING, PolicyResult.FAIL
        )
    reader = text_reader or (lambda item: item.read_text(encoding="utf-8"))
    try:
        parsed = parse_indented_yaml_scalars(reader(path), file=file)
    except (OSError, UnicodeError):
        error = SafeParserError(file, 0, key_path, "SAFE_READ_FAILED")
        return SafeTrackedFileInspection(
            file, True, False, ValueClass.PARSE_ERROR, PolicyResult.FAIL, error
        )
    if parsed.errors:
        error = parsed.errors[0]
        return SafeTrackedFileInspection(
            file, True, False, ValueClass.PARSE_ERROR, PolicyResult.FAIL, error
        )
    matches = [item for item in parsed.scalars if item.key_path == key_path]
    if len(matches) != 1:
        error = (
            None
            if not matches
            else SafeParserError(file, 0, key_path, "DUPLICATE_KEY_PATH")
        )
        return SafeTrackedFileInspection(
            file, True, False, ValueClass.MISSING, PolicyResult.FAIL, error
        )
    value_class = classify_tracked_value(key_path, matches[0].value)
    required = _REQUIRED_REFERENCE.match(matches[0].value)
    correct_reference = bool(
        required and required.group("name") == POSTGRES_PASSWORD_REFERENCE_KEY
    )
    approved_file = (
        key_path,
        matches[0].value,
    ) in _APPROVED_SHARED_DB_SECRET_REFERENCES
    return SafeTrackedFileInspection(
        file=file,
        file_exists=True,
        key_exists=True,
        value_class=value_class,
        policy_result=(
            PolicyResult.PASS
            if (
                value_class is ValueClass.REQUIRED_ENV_REFERENCE
                and correct_reference
            ) or (
                value_class is ValueClass.APPROVED_EXTERNAL_SECRET_REFERENCE
                and approved_file
            )
            else PolicyResult.FAIL
        ),
    )


@dataclass(frozen=True, slots=True)
class RequiredReferenceResolution:
    prepared: bool
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"prepared={'YES' if self.prepared else 'NO'}",
                f"error_class={self.error_class}",
            )
        )


def resolve_required_reference(
    reference: str,
    environment: Mapping[str, str],
) -> RequiredReferenceResolution:
    match = _REQUIRED_REFERENCE.match(reference)
    if not match:
        return RequiredReferenceResolution(False, "REFERENCE_NOT_REQUIRED")
    value = environment.get(match.group("name"))
    if value is None or value == "":
        return RequiredReferenceResolution(False, "REQUIRED_VALUE_MISSING")
    return RequiredReferenceResolution(True, "NONE")


@dataclass(frozen=True, slots=True)
class BindingConsistency:
    database_url_consistent: bool
    postgres_password_consistent: bool
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                "database_url_consistent="
                + ("YES" if self.database_url_consistent else "NO"),
                "postgres_password_consistent="
                + ("YES" if self.postgres_password_consistent else "NO"),
                f"error_class={self.error_class}",
            )
        )


def binding_consistency(
    database_url: str | None,
    postgres_password: str | None,
) -> BindingConsistency:
    if not database_url or not postgres_password:
        return BindingConsistency(False, False, "BINDING_KEY_MISSING")
    try:
        password = unquote(urlsplit(database_url).password or "")
    except (TypeError, ValueError):
        return BindingConsistency(False, False, "DATABASE_URL_INVALID")
    consistent = bool(password) and secrets.compare_digest(
        password,
        postgres_password,
    )
    return BindingConsistency(consistent, consistent, "NONE" if consistent else "MISMATCH")


class AuthenticationProbe(Protocol):
    def __call__(self, password: str) -> PostgresAuthenticationProbe: ...


@dataclass(frozen=True, slots=True)
class CredentialStatus:
    old_invalidated: str
    new_valid: str
    attempts: int
    repeat_rotation: str
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"old_credential_invalidated={self.old_invalidated}",
                f"new_credential_valid={self.new_valid}",
                f"attempts={self.attempts}",
                f"repeat_rotation={self.repeat_rotation}",
                f"error_class={self.error_class}",
            )
        )


def verify_credential_status(
    *,
    old_password: str,
    new_password: str,
    probe: AuthenticationProbe,
    max_attempts: int = 3,
) -> CredentialStatus:
    if max_attempts < 1 or max_attempts > 3:
        return CredentialStatus("UNRESOLVED", "UNRESOLVED", 0, "NO_DECISION", "ATTEMPT_LIMIT")
    if not old_password or not new_password:
        return CredentialStatus("UNRESOLVED", "UNRESOLVED", 0, "NO_DECISION", "CREDENTIAL_MISSING")
    for attempt in range(1, max_attempts + 1):
        try:
            old = probe(old_password)
            new = probe(new_password)
        except BaseException:
            continue
        old_invalidated = old.connection == "DENIED" and old.sqlstate == "28P01"
        new_valid = new.connection == "CONNECTED" and new.sqlstate is None
        if old.connection == "CONNECTED":
            return CredentialStatus(
                "NO",
                "YES" if new_valid else "UNRESOLVED",
                attempt,
                "YES",
                "OLD_CREDENTIAL_ACTIVE",
            )
        if old_invalidated and new_valid:
            return CredentialStatus("YES", "YES", attempt, "NO", "NONE")
    return CredentialStatus(
        "UNRESOLVED",
        "UNRESOLVED",
        max_attempts,
        "NO_DECISION",
        "STATUS_UNRESOLVED",
    )


@dataclass(frozen=True, slots=True)
class QuarantinePathDecision:
    path: str
    allowed: bool
    allowlist_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"path={self.path}",
                f"allowed={'YES' if self.allowed else 'NO'}",
                f"allowlist_class={self.allowlist_class}",
            )
        )


_CANARY_TEST = re.compile(
    r"^tests/(?:[^/]+/)*test_[^/]*controlled_runtime_canary[^/]*\.py$"
)
_CANARY_TEST_PACKAGE = re.compile(
    r"^tests/paper_controlled_runtime_canary/(?:__init__|conftest|test_[^/]+)\.py$"
)
_CANARY_DOC = re.compile(
    r"^docs/(?:[^/]+/)*(?:[^/]*controlled[^/]*runtime[^/]*canary|[^/]*paper[^/]*canary)[^/]*\.md$"
)


def classify_quarantine_path(
    path: str,
    *,
    architecture_note: str,
) -> QuarantinePathDecision:
    normalized = path.replace("\\", "/")
    forbidden_names = {
        "docker-compose.yml",
        PROTECTED_BINDING_NAME,
        "online_trader.md",
    }
    if (
        Path(normalized).name in forbidden_names
        or Path(normalized).suffix.casefold() in {".log", ".db", ".sqlite"}
        or "/.venv/" in f"/{normalized.casefold()}/"
        or "/venv/" in f"/{normalized.casefold()}/"
        or normalized.casefold().startswith("evidence")
    ):
        return QuarantinePathDecision(normalized, False, "FORBIDDEN")
    exact = {
        "app/engine_paper/controlled_runtime.py": "CONTROLLED_RUNTIME_SEMANTIC_GATE",
        "app/engine_paper/controlled_runtime_canary.py": "CANARY_MODULE_GATE",
        architecture_note.replace("\\", "/"): "EXACT_ARCHITECTURE_NOTE",
    }
    if normalized in exact:
        return QuarantinePathDecision(normalized, True, exact[normalized])
    if _CANARY_TEST.fullmatch(normalized) or _CANARY_TEST_PACKAGE.fullmatch(normalized):
        return QuarantinePathDecision(normalized, True, "CANARY_TEST")
    if _CANARY_DOC.fullmatch(normalized):
        return QuarantinePathDecision(normalized, True, "CANARY_DOC")
    return QuarantinePathDecision(normalized, False, "UNEXPECTED")


@dataclass(frozen=True, slots=True)
class RuntimeSemanticGate:
    canary_only_wiring: bool
    production_denial_weakened: bool
    live_denial_weakened: bool
    safe_defaults_changed: bool
    secret_literals_found: int
    protected_binding_access_added: bool
    non_canary_semantic_changes: int

    @property
    def passed(self) -> bool:
        return (
            self.canary_only_wiring
            and not self.production_denial_weakened
            and not self.live_denial_weakened
            and not self.safe_defaults_changed
            and self.secret_literals_found == 0
            and not self.protected_binding_access_added
            and self.non_canary_semantic_changes == 0
        )


def _top_level_units(tree: ast.Module) -> dict[tuple[str, str], str]:
    return {
        (type(node).__name__, node.name): ast.dump(node, include_attributes=False)
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def validate_controlled_runtime_semantics(
    baseline_text: str,
    candidate_text: str,
) -> RuntimeSemanticGate:
    try:
        baseline = ast.parse(baseline_text)
        candidate = ast.parse(candidate_text)
    except (SyntaxError, ValueError):
        return RuntimeSemanticGate(False, True, True, True, 0, True, 1)
    before = _top_level_units(baseline)
    after = _top_level_units(candidate)
    changed = {
        key for key in before.keys() & after.keys() if before[key] != after[key]
    }
    expected_changed = {
        ("ClassDef", "PaperControlledRuntimeAction"),
        ("ClassDef", "PaperDatabaseAccessMode"),
        ("FunctionDef", "evaluate_controlled_runtime_startup_gate"),
    }
    identifiers = {
        node.id
        for node in ast.walk(candidate)
        if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(candidate)
        if isinstance(node, ast.Attribute)
    }
    baseline_identifiers = {
        node.id
        for node in ast.walk(baseline)
        if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(baseline)
        if isinstance(node, ast.Attribute)
    }
    added_identifiers = identifiers - baseline_identifiers
    allowed_added = {
        "SINGLE_CYCLE_CANARY",
        "ISOLATED_CANARY_READ_WRITE",
        "expected_access",
        "PaperControlledRuntimeAction",
        "PaperDatabaseAccessMode",
    }
    strings_before = {
        node.value
        for node in ast.walk(baseline)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    strings_after = {
        node.value
        for node in ast.walk(candidate)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    added_strings = strings_after - strings_before
    secret_literals = sum(
        any(marker in value.casefold() for marker in _SENSITIVE_KEY_PARTS)
        or bool(_CREDENTIAL_URL.match(value))
        for value in added_strings
    )
    protected = bool(
        {"DATABASE_URL", POSTGRES_PASSWORD_REFERENCE_KEY} & added_identifiers
    )
    canary_only = (
        before.keys() == after.keys()
        and
        changed == expected_changed
        and added_identifiers <= allowed_added
        and {"SINGLE_CYCLE_CANARY", "ISOLATED_CANARY_READ_WRITE"} <= added_identifiers
    )
    return RuntimeSemanticGate(
        canary_only_wiring=canary_only,
        production_denial_weakened=False if canary_only else True,
        live_denial_weakened=False if canary_only else True,
        safe_defaults_changed=False if canary_only else True,
        secret_literals_found=secret_literals,
        protected_binding_access_added=protected,
        non_canary_semantic_changes=0 if canary_only else 1,
    )


_FORBIDDEN_EXACT_PREFIXES = (
    ("docker", "compose", "config"),
    ("docker", "exec", "env"),
    ("docker", "exec", "printenv"),
)
_FORBIDDEN_FIELDS = (".Config.Env", ".ContainerConfig.Env")


def command_is_forbidden(command: Sequence[str]) -> bool:
    normalized = tuple(str(item).casefold() for item in command)
    for prefix in _FORBIDDEN_EXACT_PREFIXES:
        folded = tuple(item.casefold() for item in prefix)
        if normalized[: len(folded)] == folded:
            return True
    if any(
        field.casefold() in item
        for field in _FORBIDDEN_FIELDS
        for item in normalized
    ):
        return True
    if normalized[:2] in {("docker", "inspect"), ("docker", "container")}:
        if normalized[:2] == ("docker", "inspect") and "--format" not in normalized:
            return True
        if (
            normalized[:2] == ("docker", "container")
            and len(normalized) > 2
            and normalized[2] == "inspect"
            and "--format" not in normalized
        ):
            return True
    return False


@dataclass(frozen=True, slots=True)
class SafeCommandResult:
    succeeded: bool
    error_class: str
    safe_output: str


def run_allowlisted_command(
    command: Sequence[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout_seconds: float = 10.0,
) -> SafeCommandResult:
    if command_is_forbidden(command):
        return SafeCommandResult(False, "FORBIDDEN_COMMAND", "")
    try:
        result = runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return SafeCommandResult(False, "COMMAND_FAILED", "")
    if result.returncode != 0:
        return SafeCommandResult(False, "NONZERO_EXIT", "")
    return SafeCommandResult(True, "NONE", result.stdout.strip())


@dataclass(frozen=True, slots=True)
class ContainerIdentity:
    name: str
    container_id: str
    image_id: str
    restart_count: int
    running: bool
    health: str
    ports: str

    def render(self) -> str:
        return "\n".join(
            (
                f"container_name={self.name}",
                f"container_id={self.container_id}",
                f"image_id={self.image_id}",
                f"restart_count={self.restart_count}",
                f"running={'YES' if self.running else 'NO'}",
                f"health={self.health}",
                f"ports={self.ports}",
            )
        )


_CONTAINER_FIELD = re.compile(r"^[A-Za-z0-9_.:>/,\[\]{} -]*$")


def parse_safe_container_record(
    name: str,
    record: str,
    ports: str,
) -> ContainerIdentity | None:
    fields = record.split("|")
    if len(fields) != 5 or not all(_CONTAINER_FIELD.fullmatch(item) for item in fields):
        return None
    if not _CONTAINER_FIELD.fullmatch(ports):
        return None
    container_id, image_id, restart, running, health = fields
    try:
        restart_count = int(restart)
    except ValueError:
        return None
    if running not in {"true", "false"} or restart_count < 0:
        return None
    return ContainerIdentity(
        name=name,
        container_id=container_id,
        image_id=image_id,
        restart_count=restart_count,
        running=running == "true",
        health=health,
        ports=ports,
    )


def inspect_container_identity(
    name: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ContainerIdentity | None:
    template = "{{.Id}}|{{.Image}}|{{.RestartCount}}|{{.State.Running}}"
    metadata = run_allowlisted_command(
        ("docker", "container", "inspect", "--format", template, name),
        runner=runner,
    )
    if not metadata.succeeded:
        return None
    health_result = run_allowlisted_command(
        (
            "docker",
            "container",
            "inspect",
            "--format",
            "{{.State.Health.Status}}",
            name,
        ),
        runner=runner,
    )
    health = health_result.safe_output if health_result.succeeded else "NONE"
    ports = run_allowlisted_command(("docker", "port", name), runner=runner)
    if not ports.succeeded:
        return None
    normalized_ports = ",".join(ports.safe_output.splitlines())
    return parse_safe_container_record(
        name,
        f"{metadata.safe_output}|{health}",
        normalized_ports,
    )


@dataclass(frozen=True, slots=True)
class RuntimeIdentityComparison:
    container_ids_unchanged: bool
    image_ids_unchanged: bool
    restart_delta: int
    identities_complete: bool


def compare_runtime_identities(
    before: Iterable[ContainerIdentity],
    after: Iterable[ContainerIdentity],
) -> RuntimeIdentityComparison:
    left = {item.name: item for item in before}
    right = {item.name: item for item in after}
    complete = bool(left) and left.keys() == right.keys()
    if not complete:
        return RuntimeIdentityComparison(False, False, 0, False)
    return RuntimeIdentityComparison(
        container_ids_unchanged=all(
            left[name].container_id == right[name].container_id for name in left
        ),
        image_ids_unchanged=all(
            left[name].image_id == right[name].image_id for name in left
        ),
        restart_delta=sum(
            right[name].restart_count - left[name].restart_count for name in left
        ),
        identities_complete=True,
    )


class DataPersistenceClass(StrEnum):
    PERSISTENT_EXTERNAL_VOLUME = "PERSISTENT_EXTERNAL_VOLUME"
    PERSISTENT_HOST_BIND = "PERSISTENT_HOST_BIND"
    MANAGED_PERSISTENT_STORAGE = "MANAGED_PERSISTENT_STORAGE"
    EPHEMERAL_CONTAINER_STORAGE = "EPHEMERAL_CONTAINER_STORAGE"
    UNPROVEN = "UNPROVEN"


class WalLevelClass(StrEnum):
    MINIMAL = "MINIMAL"
    REPLICA_OR_HIGHER = "REPLICA_OR_HIGHER"
    UNPROVEN = "UNPROVEN"


class ArchiveTimeoutClass(StrEnum):
    DISABLED = "DISABLED"
    AT_MOST_15_MINUTES = "AT_MOST_15_MINUTES"
    OVER_15_MINUTES = "OVER_15_MINUTES"
    UNPROVEN = "UNPROVEN"


@dataclass(frozen=True, slots=True)
class SafePostgresRecoveryMetadata:
    postgres_major: int | None
    archive_mode_enabled: bool | None
    wal_level_class: WalLevelClass
    archive_command_configured_boolean: bool | None
    archive_library_configured_boolean: bool | None
    archive_timeout_class: ArchiveTimeoutClass
    data_persistence_class: DataPersistenceClass
    backup_tooling_present_boolean: bool | None
    backup_destination_configured_boolean: bool | None
    backup_destination_persistence_class: DataPersistenceClass
    last_backup_metadata_present_boolean: bool | None
    last_backup_age_class: str
    wal_archive_health_class: str
    error_class: str

    def render(self) -> str:
        def boolean(value: bool | None) -> str:
            return "YES" if value is True else "NO" if value is False else "UNPROVEN"

        return "\n".join(
            (
                f"postgres_major={self.postgres_major or 'UNPROVEN'}",
                f"archive_mode_enabled={boolean(self.archive_mode_enabled)}",
                f"wal_level_class={self.wal_level_class.value}",
                f"archive_command_configured_boolean={boolean(self.archive_command_configured_boolean)}",
                f"archive_library_configured_boolean={boolean(self.archive_library_configured_boolean)}",
                f"archive_timeout_class={self.archive_timeout_class.value}",
                f"data_persistence_class={self.data_persistence_class.value}",
                f"backup_tooling_present_boolean={boolean(self.backup_tooling_present_boolean)}",
                f"backup_destination_configured_boolean={boolean(self.backup_destination_configured_boolean)}",
                f"backup_destination_persistence_class={self.backup_destination_persistence_class.value}",
                f"last_backup_metadata_present_boolean={boolean(self.last_backup_metadata_present_boolean)}",
                f"last_backup_age_class={self.last_backup_age_class}",
                f"wal_archive_health_class={self.wal_archive_health_class}",
                f"error_class={self.error_class}",
            )
        )


@dataclass(frozen=True, slots=True)
class SafePostgresCapacityMetadata:
    database_size_bytes: int | None
    error_class: str

    def render(self) -> str:
        return "\n".join((
            f"database_size_bytes={self.database_size_bytes if self.database_size_bytes is not None else 'UNPROVEN'}",
            f"error_class={self.error_class}",
        ))


def inspect_postgres_capacity_metadata(
    container: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SafePostgresCapacityMetadata:
    """Return only the numeric production database size, never names or settings."""
    result = run_allowlisted_command(
        (
            "docker", "exec", "--user", "postgres", container,
            "psql", "-U", "traders_ml", "-d", "postgres", "-AtX", "-c",
            "SELECT pg_database_size('traders_ml')",
        ),
        runner=runner,
        timeout_seconds=30,
    )
    if not result.succeeded or not re.fullmatch(r"[0-9]{1,20}", result.safe_output):
        return SafePostgresCapacityMetadata(None, "CAPACITY_UNAVAILABLE")
    size = int(result.safe_output)
    if size <= 0:
        return SafePostgresCapacityMetadata(None, "CAPACITY_INVALID")
    return SafePostgresCapacityMetadata(size, "NONE")


@dataclass(frozen=True, slots=True)
class SafePostgresVolumeIdentity:
    opaque_volume_identity: str
    error_class: str

    def render(self) -> str:
        return "\n".join((
            f"opaque_volume_identity={self.opaque_volume_identity}",
            f"error_class={self.error_class}",
        ))


def inspect_postgres_volume_identity(
    container: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SafePostgresVolumeIdentity:
    result = run_allowlisted_command(
        (
            "docker", "container", "inspect", "--format",
            "{{range .Mounts}}{{if eq .Destination \"/var/lib/postgresql/data\"}}{{.Type}}:{{.Name}}{{end}}{{end}}",
            container,
        ),
        runner=runner,
    )
    if not result.succeeded or not re.fullmatch(r"volume:[A-Za-z0-9_.-]{1,128}", result.safe_output):
        return SafePostgresVolumeIdentity("UNPROVEN", "VOLUME_IDENTITY_UNAVAILABLE")
    return SafePostgresVolumeIdentity(result.safe_output, "NONE")


@dataclass(frozen=True, slots=True)
class SafePostgresArchiveHealth:
    archived_count: int | None
    failed_count: int | None
    archived_segment_observed: bool | None
    unresolved_failure: bool | None
    last_success_age_seconds: int | None
    error_class: str

    def render(self) -> str:
        def boolean(value: bool | None) -> str:
            return "YES" if value is True else "NO" if value is False else "UNPROVEN"
        return "\n".join((
            f"archived_count={self.archived_count if self.archived_count is not None else 'UNPROVEN'}",
            f"failed_count={self.failed_count if self.failed_count is not None else 'UNPROVEN'}",
            f"archived_segment_observed={boolean(self.archived_segment_observed)}",
            f"unresolved_failure={boolean(self.unresolved_failure)}",
            f"last_success_age_seconds={self.last_success_age_seconds if self.last_success_age_seconds is not None else 'UNPROVEN'}",
            f"error_class={self.error_class}",
        ))


def inspect_postgres_archive_health(
    container: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SafePostgresArchiveHealth:
    sql = (
        "SELECT archived_count || '|' || failed_count || '|' || "
        "(last_archived_wal IS NOT NULL)::int || '|' || "
        "(last_failed_wal IS NOT NULL AND (last_archived_time IS NULL OR last_failed_time > last_archived_time))::int || '|' || "
        "COALESCE(EXTRACT(EPOCH FROM clock_timestamp() - last_archived_time)::bigint, -1) FROM pg_stat_archiver"
    )
    result = run_allowlisted_command(
        (
            "docker", "exec", "--user", "postgres", container,
            "psql", "-U", "traders_ml", "-d", "traders_ml", "-AtX", "-c", sql,
        ),
        runner=runner,
        timeout_seconds=30,
    )
    match = re.fullmatch(r"([0-9]{1,20})\|([0-9]{1,20})\|([01])\|([01])\|(-1|[0-9]{1,20})", result.safe_output) if result.succeeded else None
    if match is None:
        return SafePostgresArchiveHealth(None, None, None, None, None, "ARCHIVE_HEALTH_UNAVAILABLE")
    age = int(match.group(5))
    return SafePostgresArchiveHealth(
        int(match.group(1)), int(match.group(2)), match.group(3) == "1",
        match.group(4) == "1", None if age < 0 else age, "NONE",
    )


_SAFE_POSTGRES_METADATA = re.compile(
    r"^(?P<major>[0-9]{1,3})\|(?P<archive>on|off)\|"
    r"(?P<wal>minimal|replica|logical)\|(?P<command>[01])\|"
    r"(?P<library>[01])\|(?P<timeout>[0-9]{1,8})$"
)


def _unknown_recovery_metadata(error_class: str) -> SafePostgresRecoveryMetadata:
    return SafePostgresRecoveryMetadata(
        None, None, WalLevelClass.UNPROVEN, None, None,
        ArchiveTimeoutClass.UNPROVEN, DataPersistenceClass.UNPROVEN, None,
        None, DataPersistenceClass.UNPROVEN, None, "UNPROVEN", "UNPROVEN",
        error_class,
    )


def parse_safe_postgres_recovery_metadata(
    settings_record: str,
    persistence_record: str,
    tooling_record: str,
) -> SafePostgresRecoveryMetadata | None:
    match = _SAFE_POSTGRES_METADATA.fullmatch(settings_record.strip())
    if match is None or persistence_record not in {"volume", "bind", "tmpfs", "none"}:
        return None
    if tooling_record not in {"present", "absent"}:
        return None
    persistence = {
        "volume": DataPersistenceClass.PERSISTENT_EXTERNAL_VOLUME,
        "bind": DataPersistenceClass.PERSISTENT_HOST_BIND,
        "tmpfs": DataPersistenceClass.EPHEMERAL_CONTAINER_STORAGE,
        "none": DataPersistenceClass.EPHEMERAL_CONTAINER_STORAGE,
    }[persistence_record]
    timeout = int(match.group("timeout"))
    timeout_class = (
        ArchiveTimeoutClass.DISABLED if timeout == 0
        else ArchiveTimeoutClass.AT_MOST_15_MINUTES if timeout <= 900
        else ArchiveTimeoutClass.OVER_15_MINUTES
    )
    return SafePostgresRecoveryMetadata(
        postgres_major=int(match.group("major")),
        archive_mode_enabled=match.group("archive") == "on",
        wal_level_class=(
            WalLevelClass.MINIMAL if match.group("wal") == "minimal"
            else WalLevelClass.REPLICA_OR_HIGHER
        ),
        archive_command_configured_boolean=match.group("command") == "1",
        archive_library_configured_boolean=match.group("library") == "1",
        archive_timeout_class=timeout_class,
        data_persistence_class=persistence,
        backup_tooling_present_boolean=tooling_record == "present",
        backup_destination_configured_boolean=False,
        backup_destination_persistence_class=DataPersistenceClass.UNPROVEN,
        last_backup_metadata_present_boolean=False,
        last_backup_age_class="UNAVAILABLE",
        wal_archive_health_class="UNAVAILABLE" if match.group("archive") == "off" else "UNPROVEN",
        error_class="NONE",
    )


def inspect_postgres_recovery_metadata(
    container: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SafePostgresRecoveryMetadata:
    """Return fixed recovery enums/booleans without commands, paths, or secrets."""
    sql = (
        "SELECT current_setting('server_version_num')::int/10000 || '|' || "
        "current_setting('archive_mode') || '|' || current_setting('wal_level') || '|' || "
        "(current_setting('archive_command') <> '')::int || '|' || "
        "(current_setting('archive_library') <> '')::int || '|' || "
        "EXTRACT(EPOCH FROM current_setting('archive_timeout')::interval)::int"
    )
    settings = run_allowlisted_command(
        ("docker", "exec", "--user", "postgres", container, "psql", "-U", "traders_ml", "-d", "traders_ml", "-AtX", "-c", sql),
        runner=runner,
        timeout_seconds=15,
    )
    persistence = run_allowlisted_command(
        (
            "docker", "container", "inspect", "--format",
            "{{range .Mounts}}{{if eq .Destination \"/var/lib/postgresql/data\"}}{{.Type}}{{end}}{{end}}",
            container,
        ),
        runner=runner,
    )
    tooling = run_allowlisted_command(
        ("docker", "exec", container, "sh", "-c", "command -v pg_dump >/dev/null && printf present || printf absent"),
        runner=runner,
    )
    version = run_allowlisted_command(
        ("docker", "exec", container, "postgres", "--version"),
        runner=runner,
    )
    if not persistence.succeeded or not tooling.succeeded or not version.succeeded:
        return _unknown_recovery_metadata("RECOVERY_METADATA_INCOMPLETE")
    major_match = re.fullmatch(r"postgres \(PostgreSQL\) (?P<major>[0-9]{1,3})\.[0-9]+", version.safe_output)
    if major_match is None:
        return _unknown_recovery_metadata("POSTGRES_MAJOR_REJECTED")
    persistence_class = {
        "volume": DataPersistenceClass.PERSISTENT_EXTERNAL_VOLUME,
        "bind": DataPersistenceClass.PERSISTENT_HOST_BIND,
        "tmpfs": DataPersistenceClass.EPHEMERAL_CONTAINER_STORAGE,
        "": DataPersistenceClass.EPHEMERAL_CONTAINER_STORAGE,
    }.get(persistence.safe_output, DataPersistenceClass.UNPROVEN)
    if not settings.succeeded:
        return SafePostgresRecoveryMetadata(
            postgres_major=int(major_match.group("major")),
            archive_mode_enabled=None,
            wal_level_class=WalLevelClass.UNPROVEN,
            archive_command_configured_boolean=None,
            archive_library_configured_boolean=None,
            archive_timeout_class=ArchiveTimeoutClass.UNPROVEN,
            data_persistence_class=persistence_class,
            backup_tooling_present_boolean=tooling.safe_output == "present",
            backup_destination_configured_boolean=False,
            backup_destination_persistence_class=DataPersistenceClass.UNPROVEN,
            last_backup_metadata_present_boolean=False,
            last_backup_age_class="UNAVAILABLE",
            wal_archive_health_class="UNPROVEN",
            error_class="SETTINGS_UNAVAILABLE",
        )
    parsed = parse_safe_postgres_recovery_metadata(
        settings.safe_output, persistence.safe_output or "none", tooling.safe_output
    )
    return parsed or _unknown_recovery_metadata("RECOVERY_METADATA_REJECTED")


@dataclass(frozen=True, slots=True)
class SafeHttpStatus:
    endpoint: str
    status: int
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"endpoint={self.endpoint}",
                f"http_status={self.status}",
                f"error_class={self.error_class}",
            )
        )


def inspect_readonly_health_http(
    *,
    opener: Callable[..., object] = urlopen,
) -> SafeHttpStatus:
    endpoint = "/api/v1/health"
    try:
        response = opener(
            f"http://127.0.0.1:8765{endpoint}",
            timeout=5,
        )
        try:
            status = int(getattr(response, "status"))
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except BaseException:
        return SafeHttpStatus(endpoint, 0, "HTTP_REQUEST_FAILED")
    return SafeHttpStatus(endpoint, status, "NONE" if status == 200 else "NON_200")


@dataclass(frozen=True, slots=True)
class SafeRouteCounts:
    get_routes: int
    write_routes: int
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"get_routes={self.get_routes}",
                f"write_routes={self.write_routes}",
                f"error_class={self.error_class}",
            )
        )


def inspect_tracked_route_counts() -> SafeRouteCounts:
    try:
        from app.server_api import create_app

        def expanded(routes):
            for route in routes:
                methods = getattr(route, "methods", None)
                if methods is not None:
                    yield route
                    continue
                original = getattr(route, "original_router", None)
                if original is not None:
                    yield from expanded(getattr(original, "routes", ()))

        methods = [
            method.upper()
            for route in expanded(create_app().routes)
            for method in getattr(route, "methods", set())
        ]
    except BaseException:
        return SafeRouteCounts(0, 0, "ROUTE_INSPECTION_FAILED")
    return SafeRouteCounts(
        get_routes=sum(method == "GET" for method in methods),
        write_routes=sum(
            method in {"POST", "PUT", "PATCH", "DELETE"} for method in methods
        ),
        error_class="NONE",
    )


@dataclass(frozen=True, slots=True)
class SafeAlembicStatus:
    revision: str
    error_class: str

    def render(self) -> str:
        return "\n".join(
            (
                f"alembic_revision={self.revision}",
                f"error_class={self.error_class}",
            )
        )


_ALEMBIC_REVISION = re.compile(r"\b[0-9]{4}_[a-z0-9_]+\b")


def inspect_alembic_status(
    container: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> SafeAlembicStatus:
    result = run_allowlisted_command(
        ("docker", "exec", container, "alembic", "current"),
        runner=runner,
        timeout_seconds=15,
    )
    if not result.succeeded:
        return SafeAlembicStatus("UNRESOLVED", result.error_class)
    match = _ALEMBIC_REVISION.search(result.safe_output)
    if match is None:
        return SafeAlembicStatus("UNRESOLVED", "REVISION_UNRESOLVED")
    return SafeAlembicStatus(match.group(0), "NONE")


def render_safe_items(items: Iterable[object]) -> str:
    rendered: list[str] = []
    for item in items:
        method = getattr(item, "render", None)
        if not callable(method):
            rendered.append("error_class=UNRENDERABLE_ITEM")
            continue
        try:
            rendered.append(str(method()))
        except BaseException:
            rendered.append("error_class=SAFE_RENDER_FAILED")
    return "\n---\n".join(rendered)


__all__ = [
    "ArchiveTimeoutClass",
    "BindingConsistency",
    "ContainerIdentity",
    "CredentialStatus",
    "DataPersistenceClass",
    "PolicyResult",
    "POSTGRES_PASSWORD_KEY_PATH",
    "POSTGRES_PASSWORD_REFERENCE_KEY",
    "PROTECTED_BINDING_NAME",
    "QuarantinePathDecision",
    "RequiredReferenceResolution",
    "RuntimeIdentityComparison",
    "RuntimeSemanticGate",
    "SafeCommandResult",
    "SafeAlembicStatus",
    "SafeHttpStatus",
    "SafeParserError",
    "SafePostgresRecoveryMetadata",
    "SafeRouteCounts",
    "SafeTrackedFileInspection",
    "TrackedValue",
    "ValueClass",
    "WalLevelClass",
    "binding_consistency",
    "classify_quarantine_path",
    "classify_tracked_value",
    "command_is_forbidden",
    "compare_runtime_identities",
    "inspect_container_identity",
    "inspect_postgres_recovery_metadata",
    "inspect_alembic_status",
    "inspect_readonly_health_http",
    "inspect_tracked_route_counts",
    "inspect_tracked_compose_key",
    "parse_indented_yaml_scalars",
    "parse_safe_container_record",
    "parse_safe_postgres_recovery_metadata",
    "render_safe_items",
    "resolve_required_reference",
    "run_allowlisted_command",
    "tracked_compose_policy",
    "validate_controlled_runtime_semantics",
    "verify_credential_status",
]
