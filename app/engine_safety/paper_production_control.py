"""Host-local authoritative production PAPER kill switch.

The control plane deliberately has no database, network, API, or secret
dependency.  Both transitions and future mutating stages use the same bounded
host interlock.  A state is effective only when its canonical checksum, ACL,
and append-only audit tail reconcile.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Final, Iterator, Mapping


SCHEMA_VERSION: Final = "TRADERS_ML_PAPER_PRODUCTION_SAFETY/1"
AUDIT_SCHEMA_VERSION: Final = "TRADERS_ML_PAPER_PRODUCTION_SAFETY_AUDIT/1"
ENVIRONMENT: Final = "PRODUCTION"
MODE: Final = "PAPER"
OPERATOR_ROLE: Final = "TRADERS_LOCAL_OPERATOR"
DEFAULT_CONTROL_ROOT: Final = Path(r"D:\disk_E\game_projects\traders\production_control\paper")
STATE_NAME: Final = "state.json"
AUDIT_NAME: Final = "audit.jsonl"
INTERLOCK_NAME: Final = "interlock.lock"
PENDING_NAME: Final = "state.pending"
MAX_REASON_LENGTH: Final = 64
MAX_SYMBOLS: Final = 32
SYMBOL_RE: Final = re.compile(r"^[A-Z0-9]{2,20}$")


class SafetyControlError(RuntimeError):
    """Stable fail-closed control-plane finding."""


class PersistentState(StrEnum):
    DISABLED = "DISABLED"
    ARMED = "ARMED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class EffectiveState(StrEnum):
    DISABLED = "DISABLED"
    ARMED = "ARMED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    FAIL_CLOSED = "FAIL_CLOSED"


class MutationStage(StrEnum):
    COMMAND_INGESTION = "COMMAND_INGESTION"
    ENTRY_EXECUTION = "ENTRY_EXECUTION"
    EXIT_EVALUATION_MUTATION = "EXIT_EVALUATION_MUTATION"
    CLOSE_EXECUTION = "CLOSE_EXECUTION"


class ReasonCode(StrEnum):
    INITIALIZE_SAFE_DEFAULT = "INITIALIZE_SAFE_DEFAULT"
    OPERATOR_ARM = "OPERATOR_ARM"
    OPERATOR_DISABLE = "OPERATOR_DISABLE"
    OPERATOR_EMERGENCY_STOP = "OPERATOR_EMERGENCY_STOP"
    CLEAR_EMERGENCY_STOP = "CLEAR_EMERGENCY_STOP"
    PREPARATION_CANARY = "PREPARATION_CANARY"
    SAFETY_TEST = "SAFETY_TEST"


@dataclass(frozen=True, slots=True)
class PaperProductionArmingScope:
    max_new_commands: int
    max_open_positions: int
    allowed_symbols: tuple[str, ...]
    allowed_mode: str = MODE
    allow_live: bool = False

    def __post_init__(self) -> None:
        if not 1 <= self.max_new_commands <= 100:
            raise ValueError("INVALID_MAX_NEW_COMMANDS")
        if not 1 <= self.max_open_positions <= 100:
            raise ValueError("INVALID_MAX_OPEN_POSITIONS")
        if not 1 <= len(self.allowed_symbols) <= MAX_SYMBOLS:
            raise ValueError("INVALID_SYMBOL_SCOPE")
        if tuple(sorted(set(self.allowed_symbols))) != self.allowed_symbols:
            raise ValueError("SYMBOL_SCOPE_NOT_CANONICAL")
        if any(not SYMBOL_RE.fullmatch(symbol) for symbol in self.allowed_symbols):
            raise ValueError("INVALID_SYMBOL_SCOPE")
        if self.allowed_mode != MODE or self.allow_live:
            raise ValueError("LIVE_OR_NON_PAPER_SCOPE_DENIED")


@dataclass(frozen=True, slots=True)
class PaperProductionSafetyState:
    schema_version: str
    environment: str
    trading_mode: str
    state: PersistentState
    generation: int
    previous_state: PersistentState | None
    updated_at_utc: str
    reason_code: ReasonCode
    operator_role: str
    transition_id: str
    arming_scope: PaperProductionArmingScope | None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("UNKNOWN_SCHEMA")
        if self.environment != ENVIRONMENT or self.trading_mode != MODE:
            raise ValueError("INVALID_TARGET")
        if not isinstance(self.generation, int) or self.generation < 1:
            raise ValueError("INVALID_GENERATION")
        if self.operator_role != OPERATOR_ROLE:
            raise ValueError("INVALID_OPERATOR_ROLE")
        try:
            uuid.UUID(self.transition_id)
            datetime.fromisoformat(self.updated_at_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError) as error:
            raise ValueError("INVALID_STATE_IDENTITY") from error
        if (self.state is PersistentState.ARMED) != (self.arming_scope is not None):
            raise ValueError("INVALID_ARMING_SCOPE")


@dataclass(frozen=True, slots=True)
class ArmReadinessPreflight:
    schema_at_required_head: bool
    minimum_pitr_window_pass: bool
    market_data_adapter_ready: bool
    approval_source_adapter_ready: bool
    wal_archive_health_pass: bool
    wal_unresolved_failures_zero: bool
    pitr_chain_valid: bool
    paper_runtime_explicitly_enabled: bool
    live_disabled: bool

    @property
    def findings(self) -> tuple[str, ...]:
        checks = (
            ("PAPER_SCHEMA_NOT_AT_REQUIRED_HEAD", self.schema_at_required_head),
            ("MINIMUM_24_HOUR_PITR_WINDOW_NOT_PROVEN", self.minimum_pitr_window_pass),
            ("MARKET_DATA_ADAPTER_NOT_READY", self.market_data_adapter_ready),
            ("APPROVAL_SOURCE_ADAPTER_NOT_READY", self.approval_source_adapter_ready),
            ("WAL_ARCHIVE_HEALTH_NOT_PASS", self.wal_archive_health_pass),
            ("WAL_ARCHIVE_UNRESOLVED_FAILURES", self.wal_unresolved_failures_zero),
            ("PITR_CHAIN_INVALID", self.pitr_chain_valid),
            ("PAPER_RUNTIME_NOT_EXPLICITLY_ENABLED", self.paper_runtime_explicitly_enabled),
            ("LIVE_NOT_DISABLED", self.live_disabled),
        )
        return tuple(code for code, passed in checks if not passed)

    @property
    def passed(self) -> bool:
        return not self.findings


@dataclass(frozen=True, slots=True)
class MutationPrerequisites:
    market_data_ready: bool
    approval_candidate_eligible: bool
    backup_pitr_pass: bool
    paper_target_authorized: bool
    live_disabled: bool

    @property
    def passed(self) -> bool:
        return all(asdict(self).values())


@dataclass(frozen=True, slots=True)
class PaperProductionMutationTarget:
    environment: str
    mode: str
    symbol: str
    candidate_identity: str
    current_generation: int
    new_commands_before: int = 0
    open_positions_before: int = 0


@dataclass(frozen=True, slots=True)
class PaperProductionMutationAuthorization:
    stage: MutationStage
    transition_id: str
    generation: int
    symbol: str
    candidate_identity: str
    authorized_at_utc: str
    one_atomic_stage_only: bool = True


@dataclass(frozen=True, slots=True)
class PaperProductionSafetyControlHealth:
    state_valid: bool
    audit_valid: bool
    acl_valid: bool
    interlock_available: bool
    effective_state: EffectiveState
    generation: int | None
    arm_prerequisite_summary: tuple[str, ...]
    emergency_stop_available: bool
    health: str
    findings: tuple[str, ...]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _scope_dict(scope: PaperProductionArmingScope | None) -> dict[str, object] | None:
    return None if scope is None else {**asdict(scope), "allowed_symbols": list(scope.allowed_symbols)}


def _state_payload(state: PaperProductionSafetyState) -> dict[str, object]:
    return {
        "arming_scope": _scope_dict(state.arming_scope),
        "environment": state.environment,
        "generation": state.generation,
        "operator_role": state.operator_role,
        "previous_state": None if state.previous_state is None else state.previous_state.value,
        "reason_code": state.reason_code.value,
        "schema_version": state.schema_version,
        "state": state.state.value,
        "trading_mode": state.trading_mode,
        "transition_id": state.transition_id,
        "updated_at_utc": state.updated_at_utc,
    }


def _state_document(state: PaperProductionSafetyState) -> dict[str, object]:
    payload = _state_payload(state)
    return {**payload, "checksum_sha256": hashlib.sha256(_json_bytes(payload)).hexdigest()}


def _parse_state(raw: bytes) -> tuple[PaperProductionSafetyState, str]:
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SafetyControlError("CORRUPT_STATE") from error
    if not isinstance(document, dict) or set(document) != {
        "schema_version", "environment", "trading_mode", "state", "generation",
        "previous_state", "updated_at_utc", "reason_code", "operator_role",
        "transition_id", "arming_scope", "checksum_sha256",
    }:
        raise SafetyControlError("INVALID_STATE_SHAPE")
    checksum = document.pop("checksum_sha256")
    if not isinstance(checksum, str) or not hashlib.sha256(_json_bytes(document)).hexdigest() == checksum:
        raise SafetyControlError("STATE_CHECKSUM_MISMATCH")
    try:
        scope_raw = document["arming_scope"]
        scope = None if scope_raw is None else PaperProductionArmingScope(
            max_new_commands=scope_raw["max_new_commands"],
            max_open_positions=scope_raw["max_open_positions"],
            allowed_symbols=tuple(scope_raw["allowed_symbols"]),
            allowed_mode=scope_raw["allowed_mode"], allow_live=scope_raw["allow_live"],
        )
        state = PaperProductionSafetyState(
            schema_version=document["schema_version"], environment=document["environment"],
            trading_mode=document["trading_mode"], state=PersistentState(document["state"]),
            generation=document["generation"],
            previous_state=None if document["previous_state"] is None else PersistentState(document["previous_state"]),
            updated_at_utc=document["updated_at_utc"], reason_code=ReasonCode(document["reason_code"]),
            operator_role=document["operator_role"], transition_id=document["transition_id"], arming_scope=scope,
        )
    except (KeyError, TypeError, ValueError) as error:
        code = "UNKNOWN_SCHEMA" if document.get("schema_version") != SCHEMA_VERSION else "INVALID_STATE"
        raise SafetyControlError(code) from error
    return state, checksum


class _BoundedInterlock:
    def __init__(self, path: Path, timeout_seconds: float) -> None:
        self.path = path
        self.timeout_seconds = timeout_seconds
        self.handle = None

    def __enter__(self) -> "_BoundedInterlock":
        if not 0 <= self.timeout_seconds <= 30:
            raise SafetyControlError("INVALID_INTERLOCK_TIMEOUT")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b", buffering=0)
        if self.path.stat().st_size == 0:
            self.handle.write(b"0")
            self.handle.flush()
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self.handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as error:
                if time.monotonic() >= deadline:
                    self.handle.close()
                    self.handle = None
                    raise SafetyControlError("INTERLOCK_BUSY") from error
                time.sleep(min(0.01, max(0.001, deadline - time.monotonic())))

    def __exit__(self, *_: object) -> None:
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


class PaperProductionSafetyControl:
    def __init__(self, root: Path = DEFAULT_CONTROL_ROOT, *, interlock_timeout_seconds: float = 1.0,
                 acl_checker: Callable[[Path], bool] | None = None,
                 fault_injector: Callable[[str], None] | None = None) -> None:
        self.root = root.resolve()
        self.state_path = self.root / STATE_NAME
        self.audit_path = self.root / AUDIT_NAME
        self.interlock_path = self.root / INTERLOCK_NAME
        self.pending_path = self.root / PENDING_NAME
        self.interlock_timeout_seconds = interlock_timeout_seconds
        self._acl_checker = acl_checker
        self._fault = fault_injector or (lambda _point: None)

    def _lock(self) -> _BoundedInterlock:
        return _BoundedInterlock(self.interlock_path, self.interlock_timeout_seconds)

    def _acl_valid(self) -> bool:
        paths = (self.root, self.state_path, self.audit_path, self.interlock_path)
        if self._acl_checker is not None:
            return all(self._acl_checker(path) for path in paths)
        return restrictive_acl_tree_valid(self.root, paths)

    def _read_state_unreconciled(self) -> tuple[PaperProductionSafetyState, str]:
        try:
            return _parse_state(self.state_path.read_bytes())
        except FileNotFoundError as error:
            raise SafetyControlError("STATE_MISSING") from error
        except OSError as error:
            raise SafetyControlError("STATE_IO_FAILURE") from error

    def _read_audit(self) -> tuple[dict[str, object], ...]:
        try:
            lines = self.audit_path.read_bytes().splitlines()
        except FileNotFoundError as error:
            raise SafetyControlError("AUDIT_MISSING") from error
        except OSError as error:
            raise SafetyControlError("AUDIT_IO_FAILURE") from error
        if not lines:
            raise SafetyControlError("AUDIT_EMPTY")
        events: list[dict[str, object]] = []
        ids: set[str] = set()
        previous_after = 0
        for line in lines:
            try:
                event = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise SafetyControlError("AUDIT_CORRUPT") from error
            required = {"schema_version", "transition_id", "timestamp_utc", "environment", "mode",
                        "from_state", "to_state", "generation_before", "generation_after", "reason_code",
                        "operator_role", "result", "state_checksum_sha256"}
            if not isinstance(event, dict) or set(event) != required:
                raise SafetyControlError("AUDIT_INVALID_SHAPE")
            if event["schema_version"] != AUDIT_SCHEMA_VERSION or event["result"] != "SUCCESS":
                raise SafetyControlError("AUDIT_INVALID_EVENT")
            if event["transition_id"] in ids:
                raise SafetyControlError("AUDIT_DUPLICATE_TRANSITION_ID")
            if event["generation_before"] != previous_after or event["generation_after"] != previous_after + 1:
                raise SafetyControlError("AUDIT_GENERATION_NON_MONOTONIC")
            try:
                from_state = None if event["from_state"] is None else PersistentState(event["from_state"])
                to_state = PersistentState(event["to_state"])
            except ValueError as error:
                raise SafetyControlError("AUDIT_UNKNOWN_STATE") from error
            if not _legal_transition(from_state, to_state):
                raise SafetyControlError("AUDIT_ILLEGAL_TRANSITION")
            ids.add(str(event["transition_id"]))
            previous_after = int(event["generation_after"])
            events.append(event)
        return tuple(events)

    def read_authoritative(self) -> PaperProductionSafetyState:
        if not self._acl_valid():
            raise SafetyControlError("UNSAFE_ACL")
        state, checksum = self._read_state_unreconciled()
        latest = self._read_audit()[-1]
        if (latest["transition_id"] != state.transition_id or latest["generation_after"] != state.generation
                or latest["to_state"] != state.state.value or latest["state_checksum_sha256"] != checksum):
            raise SafetyControlError("STATE_AUDIT_MISMATCH")
        return state

    def health(self, preflight: ArmReadinessPreflight | None = None) -> PaperProductionSafetyControlHealth:
        findings: list[str] = []
        state = None
        try:
            state = self._read_state_unreconciled()[0]
        except SafetyControlError as error:
            findings.append(str(error))
        state_valid = state is not None
        try:
            audit_valid = bool(self._read_audit())
        except SafetyControlError as error:
            audit_valid = False
            findings.append(str(error))
        acl_valid = self._acl_valid()
        if not acl_valid:
            findings.append("UNSAFE_ACL")
        reconciled = False
        if state_valid and audit_valid and acl_valid:
            try:
                state = self.read_authoritative()
                reconciled = True
            except SafetyControlError as error:
                findings.append(str(error))
        try:
            with self._lock():
                interlock_available = True
        except SafetyControlError:
            interlock_available = False
            findings.append("INTERLOCK_BUSY")
        effective = EffectiveState.FAIL_CLOSED if not reconciled else EffectiveState(state.state.value)
        summary = () if preflight is None else preflight.findings
        return PaperProductionSafetyControlHealth(
            state_valid, audit_valid, acl_valid, interlock_available, effective,
            None if state is None else state.generation, summary,
            self.root.exists() and interlock_available,
            "HEALTHY" if reconciled and interlock_available else "FAIL_CLOSED",
            tuple(dict.fromkeys(findings)),
        )

    def initialize_disabled(self, *, acknowledge: bool, reason: ReasonCode = ReasonCode.INITIALIZE_SAFE_DEFAULT) -> PaperProductionSafetyState:
        if not acknowledge:
            raise SafetyControlError("PRODUCTION_CONTROL_ACKNOWLEDGEMENT_REQUIRED")
        self._fault("before lock")
        self.root.mkdir(parents=True, exist_ok=True)
        apply_restrictive_acl(self.root)
        with self._lock():
            self._fault("after lock")
            if self.state_path.exists() or self.audit_path.exists():
                raise SafetyControlError("CONTROL_ALREADY_INITIALIZED")
            state = self._new_state(None, PersistentState.DISABLED, 1, reason, None)
            self._publish(state, generation_before=0)
            apply_restrictive_acl(self.root)
            return state

    def transition(self, target: PersistentState, *, expected_generation: int, reason: ReasonCode,
                   acknowledge: bool, acknowledge_paper_arming: bool = False,
                   preflight: ArmReadinessPreflight | None = None,
                   arming_scope: PaperProductionArmingScope | None = None) -> PaperProductionSafetyState:
        if not acknowledge:
            raise SafetyControlError("PRODUCTION_CONTROL_ACKNOWLEDGEMENT_REQUIRED")
        self._fault("before lock")
        with self._lock():
            self._fault("after lock")
            current = self.read_authoritative()
            self._fault("after current read")
            if current.generation != expected_generation:
                raise SafetyControlError("STALE_GENERATION")
            if current.state is target is PersistentState.EMERGENCY_STOP:
                return current
            if not _legal_transition(current.state, target):
                raise SafetyControlError("ILLEGAL_TRANSITION")
            if target is PersistentState.ARMED:
                if not acknowledge_paper_arming:
                    raise SafetyControlError("PAPER_ARMING_ACKNOWLEDGEMENT_REQUIRED")
                if preflight is None or not preflight.passed:
                    details = "ARM_PREFLIGHT_FAILED" if preflight is None else "ARM_PREFLIGHT_FAILED:" + ",".join(preflight.findings)
                    raise SafetyControlError(details)
                if arming_scope is None:
                    raise SafetyControlError("ARMING_SCOPE_REQUIRED")
            elif arming_scope is not None:
                raise SafetyControlError("ARMING_SCOPE_ONLY_ALLOWED_FOR_ARM")
            state = self._new_state(current.state, target, current.generation + 1, reason, arming_scope)
            self._publish(state, generation_before=current.generation)
            return state

    def _new_state(self, previous: PersistentState | None, target: PersistentState, generation: int,
                   reason: ReasonCode, scope: PaperProductionArmingScope | None) -> PaperProductionSafetyState:
        return PaperProductionSafetyState(SCHEMA_VERSION, ENVIRONMENT, MODE, target, generation,
                                           previous, _utc_now(), reason, OPERATOR_ROLE,
                                           str(uuid.uuid4()), scope)

    def _publish(self, state: PaperProductionSafetyState, *, generation_before: int) -> None:
        document = _state_document(state)
        payload = _json_bytes(document)
        try:
            self.pending_path.unlink(missing_ok=True)
            with self.pending_path.open("xb") as stream:
                stream.write(payload)
                self._fault("after pending write")
                stream.flush()
                os.fsync(stream.fileno())
                self._fault("after pending flush")
            self._fault("before replace")
            os.replace(self.pending_path, self.state_path)
            self._fsync_directory()
            self._fault("after replace")
            self._fault("before audit append")
            audit = {
                "schema_version": AUDIT_SCHEMA_VERSION, "transition_id": state.transition_id,
                "timestamp_utc": state.updated_at_utc, "environment": ENVIRONMENT, "mode": MODE,
                "from_state": None if state.previous_state is None else state.previous_state.value,
                "to_state": state.state.value, "generation_before": generation_before,
                "generation_after": state.generation, "reason_code": state.reason_code.value,
                "operator_role": OPERATOR_ROLE, "result": "SUCCESS",
                "state_checksum_sha256": document["checksum_sha256"],
            }
            with self.audit_path.open("ab", buffering=0) as stream:
                line = _json_bytes(audit)
                split = max(1, len(line) // 2)
                stream.write(line[:split])
                self._fault("during audit append")
                stream.write(line[split:])
                stream.flush()
                os.fsync(stream.fileno())
            self._fault("after audit append")
            self._fsync_directory()
            apply_restrictive_acl(self.root)
            self._fault("before unlock")
        except OSError as error:
            raise SafetyControlError("ATOMIC_PUBLICATION_IO_FAILURE") from error
        finally:
            try:
                self.pending_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _fsync_directory(self) -> None:
        if os.name == "nt":
            return
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class PaperProductionMutationSafetyGate:
    def __init__(self, control: PaperProductionSafetyControl) -> None:
        self.control = control

    @contextlib.contextmanager
    def authorize_mutation(self, stage: MutationStage, target: PaperProductionMutationTarget,
                           prerequisites: MutationPrerequisites) -> Iterator[PaperProductionMutationAuthorization]:
        with self.control._lock():
            state = self.control.read_authoritative()
            if state.state is not PersistentState.ARMED:
                raise SafetyControlError(f"MUTATION_DENIED_{state.state.value}")
            if target.environment != ENVIRONMENT or target.mode != MODE:
                raise SafetyControlError("LIVE_OR_NON_PRODUCTION_TARGET_DENIED")
            if target.current_generation != state.generation:
                raise SafetyControlError("STALE_GENERATION")
            if not prerequisites.passed:
                raise SafetyControlError("INDEPENDENT_READINESS_GATE_DENIED")
            scope = state.arming_scope
            if scope is None or target.symbol not in scope.allowed_symbols:
                raise SafetyControlError("SYMBOL_SCOPE_DENIED")
            if target.new_commands_before < 0 or target.open_positions_before < 0:
                raise SafetyControlError("INVALID_MUTATION_COUNTER")
            if stage is MutationStage.COMMAND_INGESTION and target.new_commands_before >= scope.max_new_commands:
                raise SafetyControlError("NEW_COMMAND_BUDGET_EXHAUSTED")
            if target.open_positions_before >= scope.max_open_positions and stage in {
                MutationStage.COMMAND_INGESTION, MutationStage.ENTRY_EXECUTION,
            }:
                raise SafetyControlError("OPEN_POSITION_BUDGET_EXHAUSTED")
            if not target.candidate_identity or len(target.candidate_identity) > 256 or "://" in target.candidate_identity:
                raise SafetyControlError("INVALID_CANDIDATE_IDENTITY")
            yield PaperProductionMutationAuthorization(stage, state.transition_id, state.generation,
                                                        target.symbol, target.candidate_identity, _utc_now())


@dataclass(frozen=True, slots=True)
class ProductionPaperMutationComposition:
    """Future production composition requires an explicit safety dependency."""

    safety_gate: PaperProductionMutationSafetyGate

    def run_one_atomic_stage(self, stage: MutationStage, target: PaperProductionMutationTarget,
                             prerequisites: MutationPrerequisites, transaction: Callable[[], object]) -> object:
        with self.safety_gate.authorize_mutation(stage, target, prerequisites):
            return transaction()


def _legal_transition(source: PersistentState | None, target: PersistentState) -> bool:
    return (source, target) in {
        (None, PersistentState.DISABLED),
        (PersistentState.DISABLED, PersistentState.ARMED),
        (PersistentState.DISABLED, PersistentState.EMERGENCY_STOP),
        (PersistentState.ARMED, PersistentState.DISABLED),
        (PersistentState.ARMED, PersistentState.EMERGENCY_STOP),
        (PersistentState.EMERGENCY_STOP, PersistentState.DISABLED),
    }


def _current_user_sid() -> str:
    result = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"], capture_output=True, text=True,
                            timeout=5, check=False)
    match = re.search(r"S-1-[0-9-]+", result.stdout)
    if result.returncode or match is None:
        raise SafetyControlError("OPERATOR_SID_UNAVAILABLE")
    return match.group(0)


def apply_restrictive_acl(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        sid = _current_user_sid()
        result = subprocess.run([
            "icacls", str(root), "/inheritance:r", "/grant:r",
            f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F",
        ], capture_output=True, text=True, timeout=15, check=False)
        if result.returncode:
            raise SafetyControlError("ACL_APPLICATION_FAILED")
    else:
        os.chmod(root, 0o700)
        for path in root.iterdir():
            os.chmod(path, 0o600)


def restrictive_acl_valid(path: Path) -> bool:
    if not path.exists():
        return False
    if os.name == "nt":
        result = subprocess.run(["icacls", str(path)], capture_output=True, text=True, timeout=5, check=False)
        if result.returncode:
            return False
        lowered = result.stdout.lower()
        unsafe = ("everyone:(f)", "everyone:(m)", "everyone:(w)", "authenticated users:(f)",
                  "authenticated users:(m)", "builtin\\users:(f)", "builtin\\users:(m)")
        return not any(token in lowered for token in unsafe)
    return path.stat().st_mode & 0o022 == 0


def restrictive_acl_tree_valid(root: Path, required_paths: tuple[Path, ...]) -> bool:
    if not root.exists() or any(not path.exists() for path in required_paths):
        return False
    if os.name != "nt":
        return all(restrictive_acl_valid(path) for path in required_paths)
    result = subprocess.run(["icacls", str(root), "/T"], capture_output=True, text=True,
                            timeout=8, check=False)
    if result.returncode:
        return False
    lowered = result.stdout.lower()
    unsafe = ("everyone:(f)", "everyone:(m)", "everyone:(w)", "authenticated users:(f)",
              "authenticated users:(m)", "builtin\\users:(f)", "builtin\\users:(m)")
    return not any(token in lowered for token in unsafe) and all(
        str(path).lower() in lowered for path in required_paths
    )


def _preflight_from_args(args: argparse.Namespace) -> ArmReadinessPreflight:
    return ArmReadinessPreflight(
        args.schema == "0014_paper_canary_selection_policy",
        args.pitr_window_seconds >= 86400, args.market_data_ready, args.approval_source_ready,
        args.wal_archive_health == "PASS", args.wal_unresolved_failures == 0,
        args.pitr_chain_valid, args.paper_runtime_enabled, not args.live_enabled,
    )


def _require_target(args: argparse.Namespace) -> None:
    if args.environment != ENVIRONMENT or args.mode != MODE:
        raise SafetyControlError("LIVE_OR_NON_PRODUCTION_TARGET_DENIED")


def _render_state(control: PaperProductionSafetyControl, preflight: ArmReadinessPreflight | None = None) -> dict[str, object]:
    health = control.health(preflight)
    state = None
    try:
        state = control.read_authoritative()
    except SafetyControlError:
        pass
    return {
        "environment": ENVIRONMENT, "mode": MODE,
        "state": None if state is None else state.state.value,
        "effective_state": health.effective_state.value,
        "generation": health.generation,
        "updated_at": None if state is None else state.updated_at_utc,
        "reason_code": None if state is None else state.reason_code.value,
        "arming_scope": None if state is None else _scope_dict(state.arming_scope),
        "audit_health": "PASS" if health.audit_valid else "FAIL",
        "acl_health": "PASS" if health.acl_valid else "FAIL",
        "interlock_available": health.interlock_available,
        "emergency_stop_available": health.emergency_stop_available,
        "health": health.health, "findings": list(health.findings),
        "arm_prerequisite_findings": list(health.arm_prerequisite_summary),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local production PAPER safety control")
    parser.add_argument("--root", type=Path, default=DEFAULT_CONTROL_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("audit-status")
    init = sub.add_parser("initialize-disabled")
    transitions = {}
    for name in ("arm", "disable", "emergency-stop", "clear-emergency-stop"):
        command = sub.add_parser(name)
        transitions[name] = command
        command.add_argument("--environment", required=True)
        command.add_argument("--mode", required=True)
        command.add_argument("--expected-generation", required=True, type=int)
        command.add_argument("--reason", required=True, choices=tuple(item.value for item in ReasonCode))
        command.add_argument("--acknowledge-production-control", action="store_true")
    init.add_argument("--environment", required=True)
    init.add_argument("--mode", required=True)
    init.add_argument("--reason", required=True, choices=tuple(item.value for item in ReasonCode))
    init.add_argument("--acknowledge-production-control", action="store_true")
    arm = transitions["arm"]
    arm.add_argument("--acknowledge-paper-arming", action="store_true")
    arm.add_argument("--schema", required=True)
    arm.add_argument("--pitr-window-seconds", required=True, type=int)
    arm.add_argument("--market-data-ready", action="store_true")
    arm.add_argument("--approval-source-ready", action="store_true")
    arm.add_argument("--wal-archive-health", required=True, choices=("PASS", "FAIL"))
    arm.add_argument("--wal-unresolved-failures", required=True, type=int)
    arm.add_argument("--pitr-chain-valid", action="store_true")
    arm.add_argument("--paper-runtime-enabled", action="store_true")
    arm.add_argument("--live-enabled", action="store_true")
    arm.add_argument("--max-new-commands", required=True, type=int)
    arm.add_argument("--max-open-positions", required=True, type=int)
    arm.add_argument("--allowed-symbol", action="append", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    control = PaperProductionSafetyControl(args.root)
    try:
        if args.command in {"status", "audit-status"}:
            report = _render_state(control)
        else:
            _require_target(args)
            reason = ReasonCode(args.reason)
            if args.command == "initialize-disabled":
                control.initialize_disabled(acknowledge=args.acknowledge_production_control, reason=reason)
            else:
                targets = {"arm": PersistentState.ARMED, "disable": PersistentState.DISABLED,
                           "emergency-stop": PersistentState.EMERGENCY_STOP,
                           "clear-emergency-stop": PersistentState.DISABLED}
                preflight = _preflight_from_args(args) if args.command == "arm" else None
                scope = None if args.command != "arm" else PaperProductionArmingScope(
                    args.max_new_commands, args.max_open_positions, tuple(sorted(set(args.allowed_symbol))))
                control.transition(targets[args.command], expected_generation=args.expected_generation,
                                   reason=reason, acknowledge=args.acknowledge_production_control,
                                   acknowledge_paper_arming=getattr(args, "acknowledge_paper_arming", False),
                                   preflight=preflight, arming_scope=scope)
            report = _render_state(control, preflight if args.command == "arm" else None)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["health"] == "HEALTHY" else 2
    except (SafetyControlError, ValueError, OSError) as error:
        print(json.dumps({"status": "DENIED_FAIL_CLOSED", "finding": str(error)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
