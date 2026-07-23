"""Typed, bounded prompt-retry contracts for failed closed boundaries."""

from dataclasses import dataclass
from enum import StrEnum

from app.engine_market_data.errors import (
    CandleValidationError,
    DuplicateCandleConflict,
    PublicMarketDataError,
    UnsupportedTimeframeError,
)


class FailedBoundaryRetryStatus(StrEnum):
    SCHEDULED_BOUNDARY_DUE = "SCHEDULED_BOUNDARY_DUE"
    IN_FLIGHT = "IN_FLIGHT"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    RETRY_IN_FLIGHT = "RETRY_IN_FLIGHT"
    RECOVERED = "RECOVERED"
    TERMINAL_FOR_LOCAL_POLICY = "TERMINAL_FOR_LOCAL_POLICY"
    CANCELLED_ON_SHUTDOWN = "CANCELLED_ON_SHUTDOWN"


class FailedBoundaryErrorClassification(StrEnum):
    RETRYABLE_TRANSIENT = "RETRYABLE_TRANSIENT"
    RETRYABLE_RATE_LIMITED = "RETRYABLE_RATE_LIMITED"
    NON_RETRYABLE_INPUT = "NON_RETRYABLE_INPUT"
    NON_RETRYABLE_DATA_VALIDATION = "NON_RETRYABLE_DATA_VALIDATION"
    NON_RETRYABLE_PROGRAMMING = "NON_RETRYABLE_PROGRAMMING"
    CANCELLED = "CANCELLED"

    @property
    def retryable(self) -> bool:
        return self in {
            FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT,
            FailedBoundaryErrorClassification.RETRYABLE_RATE_LIMITED,
        }


@dataclass(slots=True)
class FailedBoundaryRetryRecord:
    symbol: str
    timeframe: str
    closed_until_ms: int
    expected_open_times: tuple[int, ...]
    first_failure_at_ms: int
    last_failure_at_ms: int
    next_retry_at_ms: int | None
    prompt_retry_attempt_count: int
    last_error_type: str
    last_error_summary: str
    error_classification: FailedBoundaryErrorClassification
    status: FailedBoundaryRetryStatus

    @property
    def identity(self) -> tuple[str, str, int]:
        return self.symbol, self.timeframe, self.closed_until_ms


@dataclass(frozen=True, slots=True)
class PromptRetryPolicy:
    first_delay_seconds: float = 5.0
    max_delay_seconds: float = 40.0
    horizon_seconds: float = 170.0
    max_attempts: int = 4

    def delay_ms(self, completed_prompt_attempts: int) -> int:
        delay = min(
            self.first_delay_seconds * (2**completed_prompt_attempts),
            self.max_delay_seconds,
        )
        return int(delay * 1000)

    def next_retry_at_ms(
        self,
        *,
        first_failure_at_ms: int,
        last_failure_at_ms: int,
        completed_prompt_attempts: int,
    ) -> int | None:
        if completed_prompt_attempts >= self.max_attempts:
            return None
        candidate = last_failure_at_ms + self.delay_ms(completed_prompt_attempts)
        horizon = first_failure_at_ms + int(self.horizon_seconds * 1000)
        return candidate if candidate <= horizon else None


@dataclass(slots=True)
class PromptRetryMetrics:
    scheduled: int = 0
    executed: int = 0
    recovered: int = 0
    terminal: int = 0
    duplicate_registrations: int = 0


def _exception_chain(error: BaseException) -> list[BaseException]:
    values: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        values.append(current)
        current = current.__cause__ or current.__context__
    return values


def classify_failed_boundary_error(
    error: BaseException,
) -> FailedBoundaryErrorClassification:
    chain = _exception_chain(error)
    names = {type(value).__name__ for value in chain}
    text = " | ".join(str(value).lower() for value in chain)
    statuses = {
        int(status)
        for value in chain
        if (status := getattr(getattr(value, "response", None), "status_code", None))
        is not None
    }

    if names & {"CancelledError", "KeyboardInterrupt"}:
        return FailedBoundaryErrorClassification.CANCELLED
    if statuses & {418, 429} or any(
        marker in text for marker in ("status 418", "status 429", "rate limit")
    ):
        return FailedBoundaryErrorClassification.RETRYABLE_RATE_LIMITED
    if any(isinstance(value, CandleValidationError) for value in chain):
        return FailedBoundaryErrorClassification.NON_RETRYABLE_DATA_VALIDATION
    if any(isinstance(value, DuplicateCandleConflict) for value in chain):
        return FailedBoundaryErrorClassification.NON_RETRYABLE_DATA_VALIDATION
    if any(isinstance(value, UnsupportedTimeframeError) for value in chain):
        return FailedBoundaryErrorClassification.NON_RETRYABLE_INPUT
    if any(isinstance(value, (AssertionError, TypeError, AttributeError, KeyError)) for value in chain):
        return FailedBoundaryErrorClassification.NON_RETRYABLE_PROGRAMMING
    if any(isinstance(value, (TimeoutError, ConnectionError, OSError)) for value in chain):
        return FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT
    if any(500 <= status <= 599 for status in statuses) or any(
        marker in text
        for marker in (
            "status 500",
            "status 502",
            "status 503",
            "status 504",
            "timeout",
            "timed out",
            "connection reset",
            "temporary dns",
            "exchange unavailable",
        )
    ):
        return FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT
    if any(400 <= status <= 499 for status in statuses):
        return FailedBoundaryErrorClassification.NON_RETRYABLE_INPUT
    if any(isinstance(value, ValueError) for value in chain):
        return FailedBoundaryErrorClassification.NON_RETRYABLE_INPUT
    if any(isinstance(value, PublicMarketDataError) for value in chain):
        if "request failed" in text or "temporary" in text:
            return FailedBoundaryErrorClassification.RETRYABLE_TRANSIENT
        return FailedBoundaryErrorClassification.NON_RETRYABLE_DATA_VALIDATION
    return FailedBoundaryErrorClassification.NON_RETRYABLE_PROGRAMMING
