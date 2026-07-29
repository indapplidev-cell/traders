"""Immutable persisted checkpoint contracts for future PAPER exit evaluation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256

from app.engine_market_data.timeframe import is_aligned_to_timeframe
from app.engine_safety.paper_domain import (
    ExecutionMode,
    normalize_symbol,
    require_identity,
    require_nonnegative_int,
    require_paper_mode,
    require_utc,
)


PAPER_EXIT_CURSOR_CONTRACT_VERSION = "PAPER_EXIT_EVALUATION_CURSOR_V1"
PAPER_EXIT_CURSOR_IDEMPOTENCY_VERSION = "v1"
MAX_EXIT_EVALUATION_WINDOW_CANDLES = 64
ONE_MINUTE_MS = 60_000


def _key(kind: str, *parts: object) -> str:
    values = [str(getattr(part, "value", part)).strip() for part in parts]
    if any(not value or len(value) > 128 or not value.isascii() for value in values):
        raise ValueError("bounded public cursor identity required")
    canonical = "|".join(f"{len(value)}:{value}" for value in values)
    return (
        f"paper:{kind}:{PAPER_EXIT_CURSOR_IDEMPOTENCY_VERSION}:"
        f"{sha256(canonical.encode('ascii')).hexdigest()}"
    )


def paper_exit_evaluation_cursor_id(
    *,
    position_id: str,
    mode: ExecutionMode,
    symbol: str,
    position_opened_closed_until_ms: int,
    evaluation_policy_id: str,
) -> str:
    return _key(
        "exit-cursor",
        PAPER_EXIT_CURSOR_CONTRACT_VERSION,
        require_identity(position_id, "position_id"),
        require_paper_mode(mode),
        normalize_symbol(symbol),
        require_nonnegative_int(
            position_opened_closed_until_ms, "position_opened_closed_until_ms"
        ),
        require_identity(evaluation_policy_id, "evaluation_policy_id"),
    )


def paper_exit_cursor_window_identity(
    *,
    position_id: str,
    expected_version: int,
    from_boundary_ms: int,
    to_boundary_ms: int,
    evaluation_policy_id: str,
    evaluated_close_boundaries_ms: tuple[int, ...],
) -> str:
    boundaries = ",".join(str(value) for value in evaluated_close_boundaries_ms)
    boundaries_digest = sha256(boundaries.encode("ascii")).hexdigest()
    return _key(
        "exit-cursor-advance",
        PAPER_EXIT_CURSOR_CONTRACT_VERSION,
        require_identity(position_id, "position_id"),
        require_nonnegative_int(expected_version, "expected_version"),
        require_nonnegative_int(from_boundary_ms, "from_boundary_ms"),
        require_nonnegative_int(to_boundary_ms, "to_boundary_ms"),
        require_identity(evaluation_policy_id, "evaluation_policy_id"),
        boundaries_digest,
    )


@dataclass(frozen=True, slots=True)
class PaperExitEvaluationCursor:
    cursor_id: str
    contract_version: str
    position_id: str
    mode: ExecutionMode
    symbol: str
    last_evaluated_closed_until_ms: int
    position_opened_closed_until_ms: int
    evaluation_policy_id: str
    version: int
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    causation_id: str
    last_advance_idempotency_key: str | None = None
    last_advance_from_closed_until_ms: int | None = None
    last_advance_to_closed_until_ms: int | None = None
    last_advance_expected_version: int | None = None
    last_window_identity: str | None = None

    def __post_init__(self) -> None:
        if self.contract_version != PAPER_EXIT_CURSOR_CONTRACT_VERSION:
            raise ValueError("unsupported exit cursor contract version")
        for name in (
            "cursor_id",
            "position_id",
            "evaluation_policy_id",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        object.__setattr__(self, "mode", require_paper_mode(self.mode))
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        opened = require_nonnegative_int(
            self.position_opened_closed_until_ms,
            "position_opened_closed_until_ms",
        )
        evaluated = require_nonnegative_int(
            self.last_evaluated_closed_until_ms,
            "last_evaluated_closed_until_ms",
        )
        if (
            not is_aligned_to_timeframe(opened, "1m")
            or not is_aligned_to_timeframe(evaluated, "1m")
            or evaluated < opened
        ):
            raise ValueError("cursor boundaries must be aligned and monotonic")
        require_nonnegative_int(self.version, "version")
        created = require_utc(self.created_at, "created_at")
        updated = require_utc(self.updated_at, "updated_at")
        if updated < created:
            raise ValueError("cursor timestamp regressed")
        optional = (
            self.last_advance_idempotency_key,
            self.last_advance_from_closed_until_ms,
            self.last_advance_to_closed_until_ms,
            self.last_advance_expected_version,
            self.last_window_identity,
        )
        if any(value is not None for value in optional):
            if not all(value is not None for value in optional):
                raise ValueError("cursor last-advance metadata must be complete")
            require_identity(
                self.last_advance_idempotency_key,
                "last_advance_idempotency_key",
            )
            require_identity(self.last_window_identity, "last_window_identity")
            require_nonnegative_int(
                self.last_advance_from_closed_until_ms,
                "last_advance_from_closed_until_ms",
            )
            require_nonnegative_int(
                self.last_advance_to_closed_until_ms,
                "last_advance_to_closed_until_ms",
            )
            require_nonnegative_int(
                self.last_advance_expected_version,
                "last_advance_expected_version",
            )


@dataclass(frozen=True, slots=True)
class PaperExitCursorAdvance:
    position_id: str
    expected_version: int
    from_closed_until_ms: int
    to_closed_until_ms: int
    evaluation_policy_id: str
    evaluated_close_boundaries_ms: tuple[int, ...]
    idempotency_key: str
    window_identity: str
    advanced_at: datetime
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        for name in (
            "position_id",
            "evaluation_policy_id",
            "idempotency_key",
            "window_identity",
            "correlation_id",
            "causation_id",
        ):
            object.__setattr__(
                self, name, require_identity(getattr(self, name), name)
            )
        require_nonnegative_int(self.expected_version, "expected_version")
        start = require_nonnegative_int(
            self.from_closed_until_ms, "from_closed_until_ms"
        )
        end = require_nonnegative_int(self.to_closed_until_ms, "to_closed_until_ms")
        if not isinstance(self.evaluated_close_boundaries_ms, tuple):
            raise TypeError("evaluated_close_boundaries_ms must be an immutable tuple")
        if not 1 <= len(self.evaluated_close_boundaries_ms) <= MAX_EXIT_EVALUATION_WINDOW_CANDLES:
            raise ValueError("exit evaluation window must be bounded and nonempty")
        expected = tuple(
            start + ONE_MINUTE_MS * index
            for index in range(1, len(self.evaluated_close_boundaries_ms) + 1)
        )
        if self.evaluated_close_boundaries_ms != expected or end != expected[-1]:
            raise ValueError("exit evaluation window must be exactly contiguous")
        if self.window_identity != paper_exit_cursor_window_identity(
            position_id=self.position_id,
            expected_version=self.expected_version,
            from_boundary_ms=start,
            to_boundary_ms=end,
            evaluation_policy_id=self.evaluation_policy_id,
            evaluated_close_boundaries_ms=self.evaluated_close_boundaries_ms,
        ):
            raise ValueError("exit evaluation window identity mismatch")
        if self.idempotency_key != self.window_identity:
            raise ValueError("cursor advance idempotency identity mismatch")
        require_utc(self.advanced_at, "advanced_at")


class PaperExitCursorOutcome(StrEnum):
    CURSOR_CREATED = "CURSOR_CREATED"
    CURSOR_ALREADY_EXISTS = "CURSOR_ALREADY_EXISTS"
    CURSOR_ADVANCED = "CURSOR_ADVANCED"
    CURSOR_ALREADY_ADVANCED = "CURSOR_ALREADY_ADVANCED"
    CURSOR_NOT_FOUND = "CURSOR_NOT_FOUND"
    CURSOR_STALE_VERSION = "CURSOR_STALE_VERSION"
    CURSOR_REGRESSION_REJECTED = "CURSOR_REGRESSION_REJECTED"
    CURSOR_GAP_REJECTED = "CURSOR_GAP_REJECTED"
    CURSOR_IDEMPOTENCY_CONFLICT = "CURSOR_IDEMPOTENCY_CONFLICT"
    POSITION_NOT_FOUND = "POSITION_NOT_FOUND"
    SOURCE_GRAPH_INCONSISTENT = "SOURCE_GRAPH_INCONSISTENT"
    TRANSIENT_DB_FAILURE = "TRANSIENT_DB_FAILURE"


@dataclass(frozen=True, slots=True)
class PaperExitCursorResult:
    outcome: PaperExitCursorOutcome
    cursor: PaperExitEvaluationCursor | None = None
    reason_code: str = "PAPER_EXIT_CURSOR_OK"

    @property
    def successful(self) -> bool:
        return self.outcome in {
            PaperExitCursorOutcome.CURSOR_CREATED,
            PaperExitCursorOutcome.CURSOR_ALREADY_EXISTS,
            PaperExitCursorOutcome.CURSOR_ADVANCED,
            PaperExitCursorOutcome.CURSOR_ALREADY_ADVANCED,
        }


def advanced_cursor(
    cursor: PaperExitEvaluationCursor,
    advance: PaperExitCursorAdvance,
) -> PaperExitEvaluationCursor:
    if cursor.position_id != advance.position_id:
        raise ValueError("cursor advance position mismatch")
    if cursor.evaluation_policy_id != advance.evaluation_policy_id:
        raise ValueError("cursor advance policy mismatch")
    if cursor.version != advance.expected_version:
        raise ValueError("cursor advance version mismatch")
    if cursor.last_evaluated_closed_until_ms != advance.from_closed_until_ms:
        raise ValueError("cursor advance start mismatch")
    if advance.to_closed_until_ms <= cursor.last_evaluated_closed_until_ms:
        raise ValueError("cursor advance must be monotonic")
    return replace(
        cursor,
        last_evaluated_closed_until_ms=advance.to_closed_until_ms,
        version=cursor.version + 1,
        updated_at=advance.advanced_at,
        correlation_id=advance.correlation_id,
        causation_id=advance.causation_id,
        last_advance_idempotency_key=advance.idempotency_key,
        last_advance_from_closed_until_ms=advance.from_closed_until_ms,
        last_advance_to_closed_until_ms=advance.to_closed_until_ms,
        last_advance_expected_version=advance.expected_version,
        last_window_identity=advance.window_identity,
    )
