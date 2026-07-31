"""Foreground, one-shot operator boundary for an isolated PAPER sequence.

This module deliberately contains no database discovery and no business-service
dependency.  An acceptance or operator harness supplies an isolated target
resolver; the resolved binding delegates exactly once to the authoritative
bounded-sequence canary.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, StrEnum
from pathlib import Path
from threading import Event, Lock
from types import MappingProxyType
from typing import Callable, Final, Mapping, Protocol, Sequence

from app.engine_paper.controlled_runtime_canary import (
    EXPECTED_MIGRATION_HEAD,
    PaperControlledRuntimeCanaryStage,
)
from app.engine_paper.controlled_runtime_sequence_canary import (
    MAX_SEQUENCE_STEPS,
    MIN_SEQUENCE_STEPS,
    PaperControlledRuntimeBoundedSequenceCanaryRequest,
    PaperControlledRuntimeBoundedSequenceCanaryResult,
    PaperControlledRuntimeBoundedSequenceCanaryService,
    PaperControlledRuntimeBoundedSequenceOutcome,
)
from app.engine_paper.controlled_worker import PaperLifecycleState


TASK_ID: Final = (
    "TRADERS_ML_PAPER_TRADING_OPERATOR_CONTROLLED_BOUNDED_RUNTIME_RUNNER_01"
)
CONFIGURATION_CONTRACT_VERSION: Final = "PAPER_OPERATOR_BOUNDED_CONFIGURATION_V1"
REQUEST_CONTRACT_VERSION: Final = "PAPER_OPERATOR_BOUNDED_REQUEST_V1"
ACKNOWLEDGEMENT_CONTRACT_VERSION: Final = "PAPER_OPERATOR_ACKNOWLEDGEMENT_V1"
SAFE_SUMMARY_SCHEMA_VERSION: Final = "PAPER_OPERATOR_SAFE_SUMMARY_V1"
OPERATOR_ACTION: Final = "OPERATOR_CONTROLLED_BOUNDED_RUN"
ACKNOWLEDGEMENT_PHRASE: Final = (
    "I_ACKNOWLEDGE_THIS_EXACT_FOREGROUND_ISOLATED_PAPER_SEQUENCE"
)
ALLOWED_TARGET: Final = "ISOLATED_POSTGRESQL"
ALLOWED_MODE: Final = "PAPER"
MAX_CONFIG_BYTES: Final = 65_536
MAX_REQUEST_BYTES: Final = 262_144
MAX_SAFE_SUMMARY_BYTES: Final = 16_384
MAX_SUPPLIED_INPUT_BYTES: Final = 131_072
MAX_IDENTITY_LENGTH: Final = 256
MAX_SYMBOL_LENGTH: Final = 32
MAX_TIMEOUT_SECONDS: Final = 3_600.0

_SENSITIVE_KEY_PARTS: Final = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "database_url",
    "dsn",
    "uri",
    "environment",
    "env_file",
    "protected_binding",
)
_FORBIDDEN_KEY_PARTS: Final = (
    "remote_url",
    "shell_command",
    "filesystem_glob",
    "import_path",
    "database_name",
    "database_role",
)
_FORBIDDEN_TEXT_PARTS: Final = (
    "production",
    "live",
    "shared_development_database",
    "run_continuous",
    "run_until_terminal",
    "daemon",
    "schedule",
    "watch",
    "dynamic_discovery",
    "http://",
    "https://",
    "://",
)


class PaperOperatorRuntimeExitCode(IntEnum):
    COMPLETED = 0
    VALIDATION_BLOCKED = 10
    ACKNOWLEDGEMENT_REJECTED = 11
    TARGET_REJECTED = 12
    NEXT_STEP_NOT_READY = 13
    COMPLETED_WITH_DURABLE_PREFIX_STOP = 14
    CANCELLED_BEFORE_MUTATION = 15
    CANCELLED_WITH_DURABLE_PREFIX = 16
    SEQUENCE_FAILED = 17
    POSTFLIGHT_FAILED = 18
    RESUME_STATE_AMBIGUOUS = 19
    SECURITY_POLICY_VIOLATION = 20
    CLEANUP_FAILED = 21
    INTERNAL_SAFE_FAILURE = 22


class PaperOperatorRuntimeLifecycleState(StrEnum):
    STARTING = "STARTING"
    VALIDATING = "VALIDATING"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    FINALIZING = "FINALIZING"
    EXITED = "EXITED"


class PaperOperatorRuntimeOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    VALIDATION_BLOCKED = "VALIDATION_BLOCKED"
    ACKNOWLEDGEMENT_REJECTED = "ACKNOWLEDGEMENT_REJECTED"
    TARGET_REJECTED = "TARGET_REJECTED"
    NEXT_STEP_NOT_READY = "NEXT_STEP_NOT_READY"
    DURABLE_PREFIX_STOP = "DURABLE_PREFIX_STOP"
    CANCELLED_BEFORE_MUTATION = "CANCELLED_BEFORE_MUTATION"
    CANCELLED_WITH_DURABLE_PREFIX = "CANCELLED_WITH_DURABLE_PREFIX"
    SEQUENCE_FAILED = "SEQUENCE_FAILED"
    POSTFLIGHT_FAILED = "POSTFLIGHT_FAILED"
    RESUME_STATE_AMBIGUOUS = "RESUME_STATE_AMBIGUOUS"
    SECURITY_POLICY_VIOLATION = "SECURITY_POLICY_VIOLATION"
    CLEANUP_FAILED = "CLEANUP_FAILED"
    INTERNAL_SAFE_FAILURE = "INTERNAL_SAFE_FAILURE"


class PaperOperatorManifestErrorClass(StrEnum):
    VALIDATION = "VALIDATION"
    SECURITY = "SECURITY"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    TARGET = "TARGET"
    CANCELLED = "CANCELLED"
    INTERNAL = "INTERNAL"


class PaperOperatorManifestError(ValueError):
    def __init__(self, error_class: PaperOperatorManifestErrorClass) -> None:
        super().__init__(error_class.value)
        self.error_class = error_class


def _fail(error_class: PaperOperatorManifestErrorClass) -> None:
    raise PaperOperatorManifestError(error_class)


def _normalize_key(key: object) -> str:
    if not isinstance(key, str):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    return "".join(ch for ch in key.casefold() if ch.isalnum() or ch == "_")


def _is_sensitive_key(key: object) -> bool:
    normalized = _normalize_key(key)
    return any(
        part in normalized
        for part in (*_SENSITIVE_KEY_PARTS, *_FORBIDDEN_KEY_PARTS)
    )


def _reject_sensitive_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _is_sensitive_key(key):
                _fail(PaperOperatorManifestErrorClass.SECURITY)
            _reject_sensitive_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive_keys(child)


def _reject_forbidden_text(value: object) -> None:
    if isinstance(value, str):
        folded = value.casefold()
        if any(part in folded for part in _FORBIDDEN_TEXT_PARTS):
            _fail(PaperOperatorManifestErrorClass.SECURITY)
    elif isinstance(value, dict):
        for child in value.values():
            _reject_forbidden_text(child)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_text(child)


def _json_object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        result[key] = value
    return result


def _reject_json_constant(_: str) -> object:
    _fail(PaperOperatorManifestErrorClass.VALIDATION)


def _load_json_file(path: Path, maximum_bytes: int, deadline: float) -> dict[str, object]:
    if time.monotonic() > deadline:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    if not isinstance(path, Path) or not path.is_absolute():
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    try:
        stat = path.lstat()
    except (OSError, ValueError):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    reparse_flag = int(getattr(stat, "st_file_attributes", 0)) & 0x400
    if path.is_symlink() or reparse_flag or not path.is_file():
        _fail(PaperOperatorManifestErrorClass.SECURITY)
    if stat.st_size > maximum_bytes:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_json_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except PaperOperatorManifestError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    if time.monotonic() > deadline or not isinstance(parsed, dict):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    _reject_sensitive_keys(parsed)
    _reject_forbidden_text(parsed)
    return parsed


def _exact_keys(value: Mapping[str, object], expected: frozenset[str]) -> None:
    if frozenset(value) != expected:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)


def _identity(value: object, *, symbol: bool = False) -> str:
    maximum = MAX_SYMBOL_LENGTH if symbol else MAX_IDENTITY_LENGTH
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    candidate = value.strip().upper() if symbol else value.strip()
    if any(ord(ch) < 32 for ch in candidate):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    return candidate


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    return value


def _bounded_integer(value: object, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    return value


def _timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    result = float(value)
    if not 0.01 <= result <= MAX_TIMEOUT_SECONDS:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    return result


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    try:
        candidate = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    if candidate.tzinfo is None or candidate.utcoffset() is None:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    return candidate.astimezone(timezone.utc)


def _immutable_json(value: object) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    if isinstance(value, list):
        if len(value) > 256:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        return tuple(_immutable_json(item) for item in value)
    if isinstance(value, dict):
        if len(value) > 128:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        return MappingProxyType({key: _immutable_json(child) for key, child in value.items()})
    _fail(PaperOperatorManifestErrorClass.VALIDATION)


@dataclass(frozen=True, slots=True)
class PaperOperatorBoundedRuntimeConfiguration:
    contract_version: str
    runner_action: str
    configuration_id: str
    target_kind: str
    execution_mode: str
    runtime_enabled: bool
    dry_run_enabled: bool
    explicit_paper_authorization: bool
    explicit_sequence_authorization: bool
    explicit_operator_acknowledgement: bool
    hard_sequence_limit: int
    network_enabled: bool
    polling_enabled: bool
    scheduler_enabled: bool
    daemon_enabled: bool
    safe_output_mode: str
    manifest_load_timeout_seconds: float
    target_resolution_timeout_seconds: float
    overall_runner_timeout_seconds: float
    cleanup_timeout_seconds: float

    def __post_init__(self) -> None:
        if (
            self.contract_version != CONFIGURATION_CONTRACT_VERSION
            or self.runner_action != OPERATOR_ACTION
            or self.target_kind != ALLOWED_TARGET
            or self.execution_mode != ALLOWED_MODE
            or self.runtime_enabled is not True
            or self.dry_run_enabled is not True
            or self.explicit_paper_authorization is not True
            or self.explicit_sequence_authorization is not True
            or self.explicit_operator_acknowledgement is not True
            or self.hard_sequence_limit != MAX_SEQUENCE_STEPS
            or any((self.network_enabled, self.polling_enabled, self.scheduler_enabled, self.daemon_enabled))
            or self.safe_output_mode not in {"text", "json"}
        ):
            _fail(PaperOperatorManifestErrorClass.SECURITY)


_CONFIG_KEYS: Final = frozenset(
    {
        "contract_version", "runner_action", "configuration_id", "target_kind",
        "execution_mode", "runtime_enabled", "dry_run_enabled",
        "explicit_paper_authorization", "explicit_sequence_authorization",
        "explicit_operator_acknowledgement", "hard_sequence_limit",
        "network_enabled", "polling_enabled", "scheduler_enabled", "daemon_enabled",
        "safe_output_mode", "manifest_load_timeout_seconds",
        "target_resolution_timeout_seconds", "overall_runner_timeout_seconds",
        "cleanup_timeout_seconds",
    }
)


class PaperOperatorBoundedRuntimeConfigurationLoader:
    def load(self, explicit_path: Path, *, deadline: float) -> PaperOperatorBoundedRuntimeConfiguration:
        value = _load_json_file(explicit_path, MAX_CONFIG_BYTES, deadline)
        _exact_keys(value, _CONFIG_KEYS)
        return PaperOperatorBoundedRuntimeConfiguration(
            contract_version=_identity(value["contract_version"]),
            runner_action=_identity(value["runner_action"]),
            configuration_id=_identity(value["configuration_id"]),
            target_kind=_identity(value["target_kind"]),
            execution_mode=_identity(value["execution_mode"]),
            runtime_enabled=_boolean(value["runtime_enabled"]),
            dry_run_enabled=_boolean(value["dry_run_enabled"]),
            explicit_paper_authorization=_boolean(value["explicit_paper_authorization"]),
            explicit_sequence_authorization=_boolean(value["explicit_sequence_authorization"]),
            explicit_operator_acknowledgement=_boolean(value["explicit_operator_acknowledgement"]),
            hard_sequence_limit=_bounded_integer(value["hard_sequence_limit"], 1, MAX_SEQUENCE_STEPS),
            network_enabled=_boolean(value["network_enabled"]),
            polling_enabled=_boolean(value["polling_enabled"]),
            scheduler_enabled=_boolean(value["scheduler_enabled"]),
            daemon_enabled=_boolean(value["daemon_enabled"]),
            safe_output_mode=_identity(value["safe_output_mode"]).casefold(),
            manifest_load_timeout_seconds=_timeout(value["manifest_load_timeout_seconds"]),
            target_resolution_timeout_seconds=_timeout(value["target_resolution_timeout_seconds"]),
            overall_runner_timeout_seconds=_timeout(value["overall_runner_timeout_seconds"]),
            cleanup_timeout_seconds=_timeout(value["cleanup_timeout_seconds"]),
        )


@dataclass(frozen=True, slots=True)
class PaperOperatorBoundedRuntimeAcknowledgement:
    contract_version: str
    operator_action: str
    task_id: str
    request_id: str
    sequence_id: str
    configuration_id: str
    target_identity: str
    symbol: str
    exact_ordered_stage_list: tuple[PaperControlledRuntimeCanaryStage, ...]
    exact_max_step_count: int
    expires_at: datetime
    single_use: bool
    phrase: str


@dataclass(frozen=True, slots=True)
class PaperOperatorBoundedRuntimeStepManifest:
    step_index: int
    step_id: str
    stage: PaperControlledRuntimeCanaryStage
    supplied_input_reference: str
    supplied_input: object = field(repr=False)


@dataclass(frozen=True, slots=True)
class PaperOperatorBoundedRuntimeRequestManifest:
    contract_version: str
    request_id: str
    task_id: str
    sequence_id: str
    configuration_id: str
    target_identity: str
    symbol: str
    execution_mode: str
    ordered_steps: tuple[PaperOperatorBoundedRuntimeStepManifest, ...]
    max_steps: int
    sequence_arming: bool
    acknowledgement: PaperOperatorBoundedRuntimeAcknowledgement
    created_at: datetime
    evaluated_at: datetime
    expires_at: datetime
    correlation_id: str
    result_destination_mode: str


_REQUEST_KEYS: Final = frozenset(
    {"contract_version", "request_id", "task_id", "sequence_id", "configuration_id",
     "target_identity", "symbol", "execution_mode", "ordered_steps", "max_steps",
     "sequence_arming", "acknowledgement", "created_at", "evaluated_at", "expires_at",
     "correlation_id", "result_destination_mode"}
)
_STEP_KEYS: Final = frozenset(
    {"step_index", "step_id", "stage", "supplied_input_reference", "supplied_input"}
)
_ACK_KEYS: Final = frozenset(
    {"contract_version", "operator_action", "task_id", "request_id", "sequence_id",
     "configuration_id", "target_identity", "symbol", "exact_ordered_stage_list",
     "exact_max_step_count", "expires_at", "single_use", "phrase"}
)


def _stage(value: object) -> PaperControlledRuntimeCanaryStage:
    try:
        return PaperControlledRuntimeCanaryStage(_identity(value))
    except ValueError:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)


class PaperOperatorBoundedRuntimeRequestLoader:
    def load(self, explicit_path: Path, *, deadline: float) -> PaperOperatorBoundedRuntimeRequestManifest:
        value = _load_json_file(explicit_path, MAX_REQUEST_BYTES, deadline)
        _exact_keys(value, _REQUEST_KEYS)
        raw_steps = value["ordered_steps"]
        if not isinstance(raw_steps, list) or not MIN_SEQUENCE_STEPS <= len(raw_steps) <= MAX_SEQUENCE_STEPS:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        steps: list[PaperOperatorBoundedRuntimeStepManifest] = []
        supplied_size = 0
        for index, raw in enumerate(raw_steps):
            if not isinstance(raw, dict):
                _fail(PaperOperatorManifestErrorClass.VALIDATION)
            _exact_keys(raw, _STEP_KEYS)
            supplied_size += len(json.dumps(raw["supplied_input"], separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
            if supplied_size > MAX_SUPPLIED_INPUT_BYTES:
                _fail(PaperOperatorManifestErrorClass.VALIDATION)
            step = PaperOperatorBoundedRuntimeStepManifest(
                step_index=_bounded_integer(raw["step_index"], 0, MAX_SEQUENCE_STEPS - 1),
                step_id=_identity(raw["step_id"]),
                stage=_stage(raw["stage"]),
                supplied_input_reference=_identity(raw["supplied_input_reference"]),
                supplied_input=_immutable_json(raw["supplied_input"]),
            )
            if step.step_index != index:
                _fail(PaperOperatorManifestErrorClass.VALIDATION)
            steps.append(step)
        raw_ack = value["acknowledgement"]
        if not isinstance(raw_ack, dict):
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        _exact_keys(raw_ack, _ACK_KEYS)
        raw_ack_stages = raw_ack["exact_ordered_stage_list"]
        if not isinstance(raw_ack_stages, list) or len(raw_ack_stages) > MAX_SEQUENCE_STEPS:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        acknowledgement = PaperOperatorBoundedRuntimeAcknowledgement(
            contract_version=_identity(raw_ack["contract_version"]),
            operator_action=_identity(raw_ack["operator_action"]),
            task_id=_identity(raw_ack["task_id"]),
            request_id=_identity(raw_ack["request_id"]),
            sequence_id=_identity(raw_ack["sequence_id"]),
            configuration_id=_identity(raw_ack["configuration_id"]),
            target_identity=_identity(raw_ack["target_identity"]),
            symbol=_identity(raw_ack["symbol"], symbol=True),
            exact_ordered_stage_list=tuple(_stage(item) for item in raw_ack_stages),
            exact_max_step_count=_bounded_integer(raw_ack["exact_max_step_count"], 1, MAX_SEQUENCE_STEPS),
            expires_at=_utc(raw_ack["expires_at"]),
            single_use=_boolean(raw_ack["single_use"]),
            phrase=_identity(raw_ack["phrase"]),
        )
        return PaperOperatorBoundedRuntimeRequestManifest(
            contract_version=_identity(value["contract_version"]),
            request_id=_identity(value["request_id"]),
            task_id=_identity(value["task_id"]),
            sequence_id=_identity(value["sequence_id"]),
            configuration_id=_identity(value["configuration_id"]),
            target_identity=_identity(value["target_identity"]),
            symbol=_identity(value["symbol"], symbol=True),
            execution_mode=_identity(value["execution_mode"]),
            ordered_steps=tuple(steps),
            max_steps=_bounded_integer(value["max_steps"], 1, MAX_SEQUENCE_STEPS),
            sequence_arming=_boolean(value["sequence_arming"]),
            acknowledgement=acknowledgement,
            created_at=_utc(value["created_at"]),
            evaluated_at=_utc(value["evaluated_at"]),
            expires_at=_utc(value["expires_at"]),
            correlation_id=_identity(value["correlation_id"]),
            result_destination_mode=_identity(value["result_destination_mode"]).casefold(),
        )


@dataclass(frozen=True, slots=True)
class PaperOperatorControlledBoundedRuntimeRunRequest:
    configuration_path: Path
    request_path: Path


class PaperOperatorBoundedSequenceRequestBuilder(Protocol):
    def __call__(
        self,
        configuration: PaperOperatorBoundedRuntimeConfiguration,
        manifest: PaperOperatorBoundedRuntimeRequestManifest,
        cancellation: "PaperOperatorCooperativeCancellation",
    ) -> PaperControlledRuntimeBoundedSequenceCanaryRequest: ...


@dataclass(frozen=True, slots=True)
class PaperOperatorResolvedIsolatedTarget:
    target_identity: str
    task_owned: bool
    migration_head: str
    sequence_service: PaperControlledRuntimeBoundedSequenceCanaryService = field(repr=False)
    request_builder: PaperOperatorBoundedSequenceRequestBuilder = field(repr=False)
    cleanup: Callable[[], bool] = field(repr=False)


class PaperOperatorIsolatedTargetResolver(Protocol):
    def resolve(
        self, target_identity: str, *, deadline: float
    ) -> PaperOperatorResolvedIsolatedTarget: ...


class PaperOperatorRejectingIsolatedTargetResolver:
    def resolve(self, target_identity: str, *, deadline: float) -> PaperOperatorResolvedIsolatedTarget:
        del target_identity, deadline
        _fail(PaperOperatorManifestErrorClass.TARGET)


class PaperOperatorCooperativeCancellation:
    def __init__(self, *, monotonic: Callable[[], float] | None = None) -> None:
        self._event = Event()
        self._monotonic = monotonic or time.monotonic
        self._deadline: float | None = None

    def cancel(self) -> None:
        self._event.set()

    def set_deadline(self, deadline: float) -> None:
        self._deadline = deadline

    def is_cancelled(self) -> bool:
        return self._event.is_set() or (
            self._deadline is not None and self._monotonic() > self._deadline
        )


class PaperOperatorSignalAdapter:
    def __init__(self, cancellation: PaperOperatorCooperativeCancellation) -> None:
        self._cancellation = cancellation
        self._previous: dict[int, object] = {}
        self._installed = False

    def _handle(self, _signum: int, _frame: object) -> None:
        self._cancellation.cancel()

    def install(self) -> None:
        if self._installed:
            return
        for candidate in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if candidate is None:
                continue
            try:
                self._previous[int(candidate)] = signal.getsignal(candidate)
                signal.signal(candidate, self._handle)
            except (OSError, RuntimeError, ValueError):
                continue
        self._installed = True

    def restore(self) -> None:
        if not self._installed:
            return
        for signum, previous in self._previous.items():
            try:
                signal.signal(signum, previous)
            except (OSError, RuntimeError, ValueError):
                pass
        self._installed = False


@dataclass(frozen=True, slots=True)
class PaperOperatorRuntimeSafeSummary:
    schema_version: str
    runner_outcome: PaperOperatorRuntimeOutcome
    exit_code: PaperOperatorRuntimeExitCode
    correlation_id: str
    requested_step_count: int
    completed_step_count: int
    failed_step_count: int
    durable_prefix_length: int
    next_resumable_step_index: int | None
    worker_invocation_count: int
    cleanup_outcome: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "runner_outcome": self.runner_outcome.value,
            "exit_code": int(self.exit_code),
            "correlation_id": self.correlation_id,
            "requested_step_count": self.requested_step_count,
            "completed_step_count": self.completed_step_count,
            "failed_step_count": self.failed_step_count,
            "durable_prefix_length": self.durable_prefix_length,
            "next_resumable_step_index": self.next_resumable_step_index,
            "worker_invocation_count": self.worker_invocation_count,
            "cleanup_outcome": self.cleanup_outcome,
        }

    def render(self, output_format: str) -> str:
        if output_format == "json":
            rendered = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        else:
            rendered = " ".join(f"{key}={value}" for key, value in self.as_dict().items())
        if len(rendered.encode("utf-8")) > MAX_SAFE_SUMMARY_BYTES:
            raise ValueError("SAFE_SUMMARY_BOUND_EXCEEDED")
        return rendered


@dataclass(frozen=True, slots=True)
class PaperOperatorControlledBoundedRuntimeRunResult:
    runner_outcome: PaperOperatorRuntimeOutcome
    configuration_outcome: str
    request_outcome: str
    acknowledgement_outcome: str
    target_validation_outcome: str
    sequence_outcome: str
    requested_step_count: int
    completed_step_count: int
    failed_step_count: int
    durable_prefix_length: int
    next_resumable_step_index: int | None
    initial_lifecycle_state: PaperLifecycleState | None
    final_lifecycle_state: PaperLifecycleState | None
    worker_invocation_count: int
    budget_outcome: str
    cancellation_fault_classification: str
    cleanup_outcome: str
    exit_code: PaperOperatorRuntimeExitCode
    correlation_id: str
    initial_runner_state: PaperOperatorRuntimeLifecycleState
    final_runner_state: PaperOperatorRuntimeLifecycleState

    def safe_summary(self) -> PaperOperatorRuntimeSafeSummary:
        return PaperOperatorRuntimeSafeSummary(
            SAFE_SUMMARY_SCHEMA_VERSION, self.runner_outcome, self.exit_code,
            self.correlation_id, self.requested_step_count, self.completed_step_count,
            self.failed_step_count, self.durable_prefix_length,
            self.next_resumable_step_index, self.worker_invocation_count,
            self.cleanup_outcome,
        )


def _validate_acknowledgement(
    configuration: PaperOperatorBoundedRuntimeConfiguration,
    manifest: PaperOperatorBoundedRuntimeRequestManifest,
    evaluated_at: datetime,
) -> None:
    ack = manifest.acknowledgement
    expected = (
        ack.contract_version == ACKNOWLEDGEMENT_CONTRACT_VERSION
        and ack.operator_action == OPERATOR_ACTION
        and ack.task_id == manifest.task_id == TASK_ID
        and ack.request_id == manifest.request_id
        and ack.sequence_id == manifest.sequence_id
        and ack.configuration_id == manifest.configuration_id == configuration.configuration_id
        and ack.target_identity == manifest.target_identity
        and ack.symbol == manifest.symbol
        and ack.exact_ordered_stage_list == tuple(step.stage for step in manifest.ordered_steps)
        and ack.exact_max_step_count == manifest.max_steps == len(manifest.ordered_steps)
        and ack.expires_at >= evaluated_at
        and manifest.expires_at >= evaluated_at
        and ack.single_use is True
        and ack.phrase == ACKNOWLEDGEMENT_PHRASE
        and manifest.contract_version == REQUEST_CONTRACT_VERSION
        and manifest.execution_mode == ALLOWED_MODE
        and manifest.sequence_arming is True
        and manifest.result_destination_mode in {"stdout", "explicit_safe_file"}
    )
    if not expected:
        _fail(PaperOperatorManifestErrorClass.ACKNOWLEDGEMENT)


def _translate_sequence(
    result: PaperControlledRuntimeBoundedSequenceCanaryResult,
) -> tuple[PaperOperatorRuntimeOutcome, PaperOperatorRuntimeExitCode]:
    outcome = result.overall_outcome
    if outcome in {
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_AFTER_COMPLETION,
    }:
        return PaperOperatorRuntimeOutcome.COMPLETED, PaperOperatorRuntimeExitCode.COMPLETED
    if outcome is PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_RESUME_STATE_AMBIGUOUS:
        return PaperOperatorRuntimeOutcome.RESUME_STATE_AMBIGUOUS, PaperOperatorRuntimeExitCode.RESUME_STATE_AMBIGUOUS
    if outcome is PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_BEFORE_FIRST_MUTATION:
        return PaperOperatorRuntimeOutcome.CANCELLED_BEFORE_MUTATION, PaperOperatorRuntimeExitCode.CANCELLED_BEFORE_MUTATION
    if outcome is PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX:
        return PaperOperatorRuntimeOutcome.CANCELLED_WITH_DURABLE_PREFIX, PaperOperatorRuntimeExitCode.CANCELLED_WITH_DURABLE_PREFIX
    if outcome in {
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_EXPECTED_STATE_MISMATCH,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PLAN_INVALID,
    }:
        return PaperOperatorRuntimeOutcome.NEXT_STEP_NOT_READY, PaperOperatorRuntimeExitCode.NEXT_STEP_NOT_READY
    if outcome in {
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_TARGET_INVALID,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CONFIGURATION_INVALID,
        PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_AUTHORIZATION_INVALID,
    }:
        return PaperOperatorRuntimeOutcome.VALIDATION_BLOCKED, PaperOperatorRuntimeExitCode.VALIDATION_BLOCKED
    if result.durable_completed_prefix:
        return PaperOperatorRuntimeOutcome.DURABLE_PREFIX_STOP, PaperOperatorRuntimeExitCode.COMPLETED_WITH_DURABLE_PREFIX_STOP
    return PaperOperatorRuntimeOutcome.SEQUENCE_FAILED, PaperOperatorRuntimeExitCode.SEQUENCE_FAILED


class PaperOperatorControlledBoundedRuntimeRunner:
    def __init__(
        self,
        target_resolver: PaperOperatorIsolatedTargetResolver,
        *,
        configuration_loader: PaperOperatorBoundedRuntimeConfigurationLoader | None = None,
        request_loader: PaperOperatorBoundedRuntimeRequestLoader | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        self._target_resolver = target_resolver
        self._configuration_loader = configuration_loader or PaperOperatorBoundedRuntimeConfigurationLoader()
        self._request_loader = request_loader or PaperOperatorBoundedRuntimeRequestLoader()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self._acknowledgement_uses: set[tuple[str, str]] = set()
        self._acknowledgement_lock = Lock()

    def run(
        self,
        request: PaperOperatorControlledBoundedRuntimeRunRequest,
        *,
        cancellation: PaperOperatorCooperativeCancellation | None = None,
    ) -> PaperOperatorControlledBoundedRuntimeRunResult:
        token = cancellation or PaperOperatorCooperativeCancellation(
            monotonic=self._monotonic
        )
        signal_adapter = PaperOperatorSignalAdapter(token)
        signal_adapter.install()
        initial_state = PaperOperatorRuntimeLifecycleState.STARTING
        configuration_outcome = request_outcome = acknowledgement_outcome = "NOT_RUN"
        target_outcome = sequence_outcome = "NOT_RUN"
        correlation_id = "UNAVAILABLE"
        requested_steps = 0
        resolved: PaperOperatorResolvedIsolatedTarget | None = None
        sequence_result: PaperControlledRuntimeBoundedSequenceCanaryResult | None = None
        cleanup_outcome = "PASS"
        outcome = PaperOperatorRuntimeOutcome.INTERNAL_SAFE_FAILURE
        exit_code = PaperOperatorRuntimeExitCode.INTERNAL_SAFE_FAILURE
        start = self._monotonic()
        cleanup_timeout = 5.0
        try:
            load_deadline = start + 5.0
            configuration = self._configuration_loader.load(request.configuration_path, deadline=load_deadline)
            configuration_outcome = "PASS"
            cleanup_timeout = configuration.cleanup_timeout_seconds
            overall_deadline = start + configuration.overall_runner_timeout_seconds
            token.set_deadline(overall_deadline)
            load_deadline = min(overall_deadline, start + configuration.manifest_load_timeout_seconds)
            manifest = self._request_loader.load(request.request_path, deadline=load_deadline)
            request_outcome = "PASS"
            correlation_id = manifest.correlation_id
            requested_steps = len(manifest.ordered_steps)
            if token.is_cancelled() or self._monotonic() > overall_deadline:
                _fail(PaperOperatorManifestErrorClass.CANCELLED)
            _validate_acknowledgement(configuration, manifest, self._clock())
            acknowledgement_key = (manifest.request_id, manifest.sequence_id)
            with self._acknowledgement_lock:
                if acknowledgement_key in self._acknowledgement_uses:
                    _fail(PaperOperatorManifestErrorClass.ACKNOWLEDGEMENT)
                self._acknowledgement_uses.add(acknowledgement_key)
            acknowledgement_outcome = "PASS"
            target_deadline = min(overall_deadline, self._monotonic() + configuration.target_resolution_timeout_seconds)
            resolved = self._target_resolver.resolve(manifest.target_identity, deadline=target_deadline)
            if (
                self._monotonic() > target_deadline
                or resolved.target_identity != manifest.target_identity
                or resolved.task_owned is not True
                or resolved.migration_head != EXPECTED_MIGRATION_HEAD
            ):
                _fail(PaperOperatorManifestErrorClass.TARGET)
            target_outcome = "PASS"
            if token.is_cancelled() or self._monotonic() > overall_deadline:
                _fail(PaperOperatorManifestErrorClass.CANCELLED)
            authoritative_request = resolved.request_builder(configuration, manifest, token)
            if (
                authoritative_request.request_id != manifest.request_id
                or tuple(step.expected_stage for step in authoritative_request.plan.ordered_step_plans)
                != tuple(step.stage for step in manifest.ordered_steps)
                or len(authoritative_request.ordered_cycle_requests) != len(manifest.ordered_steps)
            ):
                _fail(PaperOperatorManifestErrorClass.VALIDATION)
            sequence_result = resolved.sequence_service.run(authoritative_request)
            sequence_outcome = sequence_result.overall_outcome.value
            outcome, exit_code = _translate_sequence(sequence_result)
        except PaperOperatorManifestError as exc:
            if exc.error_class is PaperOperatorManifestErrorClass.SECURITY:
                outcome, exit_code = PaperOperatorRuntimeOutcome.SECURITY_POLICY_VIOLATION, PaperOperatorRuntimeExitCode.SECURITY_POLICY_VIOLATION
            elif exc.error_class is PaperOperatorManifestErrorClass.ACKNOWLEDGEMENT:
                outcome, exit_code = PaperOperatorRuntimeOutcome.ACKNOWLEDGEMENT_REJECTED, PaperOperatorRuntimeExitCode.ACKNOWLEDGEMENT_REJECTED
            elif exc.error_class is PaperOperatorManifestErrorClass.TARGET:
                outcome, exit_code = PaperOperatorRuntimeOutcome.TARGET_REJECTED, PaperOperatorRuntimeExitCode.TARGET_REJECTED
            elif exc.error_class is PaperOperatorManifestErrorClass.CANCELLED:
                outcome, exit_code = PaperOperatorRuntimeOutcome.CANCELLED_BEFORE_MUTATION, PaperOperatorRuntimeExitCode.CANCELLED_BEFORE_MUTATION
            else:
                outcome, exit_code = PaperOperatorRuntimeOutcome.VALIDATION_BLOCKED, PaperOperatorRuntimeExitCode.VALIDATION_BLOCKED
        except KeyboardInterrupt:
            token.cancel()
            outcome, exit_code = PaperOperatorRuntimeOutcome.CANCELLED_BEFORE_MUTATION, PaperOperatorRuntimeExitCode.CANCELLED_BEFORE_MUTATION
        except BaseException:
            outcome, exit_code = PaperOperatorRuntimeOutcome.INTERNAL_SAFE_FAILURE, PaperOperatorRuntimeExitCode.INTERNAL_SAFE_FAILURE
        finally:
            cleanup_start = self._monotonic()
            if resolved is not None:
                try:
                    cleanup_outcome = "PASS" if resolved.cleanup() else "FAILED"
                except BaseException:
                    cleanup_outcome = "FAILED"
            signal_adapter.restore()
            if self._monotonic() - cleanup_start > cleanup_timeout:
                cleanup_outcome = "FAILED"
            if cleanup_outcome != "PASS":
                outcome, exit_code = PaperOperatorRuntimeOutcome.CLEANUP_FAILED, PaperOperatorRuntimeExitCode.CLEANUP_FAILED
        return PaperOperatorControlledBoundedRuntimeRunResult(
            runner_outcome=outcome,
            configuration_outcome=configuration_outcome,
            request_outcome=request_outcome,
            acknowledgement_outcome=acknowledgement_outcome,
            target_validation_outcome=target_outcome,
            sequence_outcome=sequence_outcome,
            requested_step_count=requested_steps,
            completed_step_count=0 if sequence_result is None else sequence_result.completed_step_count,
            failed_step_count=0 if sequence_result is None else sequence_result.failed_step_count,
            durable_prefix_length=0 if sequence_result is None else sequence_result.durable_completed_prefix,
            next_resumable_step_index=None if sequence_result is None else sequence_result.next_resumable_step_index,
            initial_lifecycle_state=None if sequence_result is None else sequence_result.initial_persisted_state,
            final_lifecycle_state=None if sequence_result is None else sequence_result.final_persisted_state,
            worker_invocation_count=0 if sequence_result is None else sequence_result.total_worker_calls,
            budget_outcome="NOT_RUN" if sequence_result is None else sequence_result.aggregate_budget_result,
            cancellation_fault_classification="NONE" if sequence_result is None else sequence_result.cancellation_fault_classification,
            cleanup_outcome=cleanup_outcome,
            exit_code=exit_code,
            correlation_id=correlation_id,
            initial_runner_state=initial_state,
            final_runner_state=PaperOperatorRuntimeLifecycleState.EXITED,
        )


_FORBIDDEN_CLI_OPTIONS: Final = frozenset(
    {"--production", "--live", "--daemon", "--schedule", "--poll", "--watch",
     "--continuous", "--auto-retry", "--database-url", "--password", "--env-file",
     "--compose-file"}
)


@dataclass(frozen=True, slots=True)
class _CliArguments:
    config: Path
    request: Path
    summary_format: str
    result_path: Path | None


def _parse_cli(argv: Sequence[str]) -> _CliArguments:
    if any(item.casefold().split("=", 1)[0] in _FORBIDDEN_CLI_OPTIONS for item in argv):
        _fail(PaperOperatorManifestErrorClass.SECURITY)
    allowed_values = {"--config", "--request", "--summary-format", "--result-path"}
    allowed_flags = {"--operator-controlled-bounded-run"}
    values: dict[str, str] = {}
    flags: set[str] = set()
    iterator = iter(argv)
    for option in iterator:
        if option in allowed_flags:
            if option in flags:
                _fail(PaperOperatorManifestErrorClass.VALIDATION)
            flags.add(option)
            continue
        if option not in allowed_values or option in values:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
        try:
            values[option] = next(iterator)
        except StopIteration:
            _fail(PaperOperatorManifestErrorClass.VALIDATION)
    if "--operator-controlled-bounded-run" not in flags or "--config" not in values or "--request" not in values:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    summary_format = values.get("--summary-format", "text").casefold()
    if summary_format not in {"text", "json"}:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    result_path = Path(os.path.abspath(values["--result-path"])) if "--result-path" in values else None
    return _CliArguments(
        Path(os.path.abspath(values["--config"])),
        Path(os.path.abspath(values["--request"])),
        summary_format,
        result_path,
    )


def _atomic_safe_write(path: Path, content: str) -> None:
    if not path.is_absolute() or not path.parent.is_dir() or path.exists():
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    parent_stat = path.parent.lstat()
    if path.parent.is_symlink() or int(getattr(parent_stat, "st_file_attributes", 0)) & 0x400:
        _fail(PaperOperatorManifestErrorClass.SECURITY)
    repository_root = Path(__file__).resolve().parents[2]
    try:
        path.relative_to(repository_root)
    except ValueError:
        pass
    else:
        _fail(PaperOperatorManifestErrorClass.SECURITY)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_SAFE_SUMMARY_BYTES:
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        _fail(PaperOperatorManifestErrorClass.VALIDATION)
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _safe_cli_failure(exit_code: PaperOperatorRuntimeExitCode) -> PaperOperatorRuntimeSafeSummary:
    outcome = (
        PaperOperatorRuntimeOutcome.SECURITY_POLICY_VIOLATION
        if exit_code is PaperOperatorRuntimeExitCode.SECURITY_POLICY_VIOLATION
        else PaperOperatorRuntimeOutcome.VALIDATION_BLOCKED
    )
    return PaperOperatorRuntimeSafeSummary(
        SAFE_SUMMARY_SCHEMA_VERSION, outcome, exit_code, "UNAVAILABLE", 0, 0, 0,
        0, None, 0, "PASS",
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: PaperOperatorControlledBoundedRuntimeRunner | None = None,
) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    try:
        parsed = _parse_cli(arguments)
    except PaperOperatorManifestError as exc:
        code = (
            PaperOperatorRuntimeExitCode.SECURITY_POLICY_VIOLATION
            if exc.error_class is PaperOperatorManifestErrorClass.SECURITY
            else PaperOperatorRuntimeExitCode.VALIDATION_BLOCKED
        )
        summary = _safe_cli_failure(code)
        print(summary.render("text"))
        print(f"runner_error_class={exc.error_class.value}", file=sys.stderr)
        return int(code)
    active_runner = runner or PaperOperatorControlledBoundedRuntimeRunner(
        PaperOperatorRejectingIsolatedTargetResolver()
    )
    result = active_runner.run(
        PaperOperatorControlledBoundedRuntimeRunRequest(parsed.config, parsed.request)
    )
    rendered = result.safe_summary().render(parsed.summary_format)
    try:
        if parsed.result_path is not None:
            _atomic_safe_write(parsed.result_path, rendered)
        print(rendered)
    except PaperOperatorManifestError as exc:
        summary = _safe_cli_failure(PaperOperatorRuntimeExitCode.SECURITY_POLICY_VIOLATION)
        print(summary.render("text"))
        print(f"runner_error_class={exc.error_class.value}", file=sys.stderr)
        return int(PaperOperatorRuntimeExitCode.SECURITY_POLICY_VIOLATION)
    if result.exit_code != PaperOperatorRuntimeExitCode.COMPLETED:
        print(f"runner_error_class={result.runner_outcome.value}", file=sys.stderr)
    return int(result.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "ACKNOWLEDGEMENT_CONTRACT_VERSION", "ACKNOWLEDGEMENT_PHRASE",
    "CONFIGURATION_CONTRACT_VERSION", "MAX_CONFIG_BYTES", "MAX_REQUEST_BYTES",
    "OPERATOR_ACTION", "PaperOperatorBoundedRuntimeAcknowledgement",
    "PaperOperatorBoundedRuntimeConfiguration",
    "PaperOperatorBoundedRuntimeConfigurationLoader",
    "PaperOperatorBoundedRuntimeRequestLoader",
    "PaperOperatorBoundedRuntimeRequestManifest",
    "PaperOperatorControlledBoundedRuntimeRunRequest",
    "PaperOperatorControlledBoundedRuntimeRunResult",
    "PaperOperatorControlledBoundedRuntimeRunner",
    "PaperOperatorCooperativeCancellation", "PaperOperatorIsolatedTargetResolver",
    "PaperOperatorResolvedIsolatedTarget", "PaperOperatorRuntimeExitCode",
    "PaperOperatorRuntimeSafeSummary", "REQUEST_CONTRACT_VERSION", "TASK_ID", "main",
)
