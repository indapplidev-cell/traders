from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SampleTransport(StrEnum):
    SUCCESS = "SUCCESS"
    HTTP_ERROR = "HTTP_ERROR"
    TIMEOUT = "TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    PARSE_ERROR = "PARSE_ERROR"


class RuntimeHealthClassification(StrEnum):
    CURRENT = "CURRENT"
    WITHIN_GRACE = "WITHIN_GRACE"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class ClassificationReasonCode(StrEnum):
    CLASSIFIED_CURRENT = "CLASSIFIED_CURRENT"
    CLASSIFIED_WITHIN_GRACE = "CLASSIFIED_WITHIN_GRACE"
    CLASSIFIED_DEADLINE_EXPIRED = "CLASSIFIED_DEADLINE_EXPIRED"
    CLASSIFIED_DEGRADED = "CLASSIFIED_DEGRADED"
    GENUINELY_UNKNOWN_RUNTIME_STATE = "GENUINELY_UNKNOWN_RUNTIME_STATE"
    CONTRADICTORY_HEALTH_SIGNALS = "CONTRADICTORY_HEALTH_SIGNALS"
    REQUIRED_HEALTH_FIELD_MISSING = "REQUIRED_HEALTH_FIELD_MISSING"
    HEALTH_FIELD_TYPE_MISMATCH = "HEALTH_FIELD_TYPE_MISMATCH"
    UNKNOWN_HEALTH_ENUM = "UNKNOWN_HEALTH_ENUM"
    INVALID_HEALTH_ROOT_TYPE = "INVALID_HEALTH_ROOT_TYPE"
    HEALTH_JSON_PARSE_FAILED = "HEALTH_JSON_PARSE_FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class PhaseName(StrEnum):
    NORMAL = "NORMAL"
    BOUNDARY = "BOUNDARY"
    NORMAL_AFTER_BOUNDARY = "NORMAL_AFTER_BOUNDARY"


@dataclass(frozen=True, slots=True)
class ScheduledSample:
    sequence_id: int
    phase_id: int
    phase_name: PhaseName
    scheduled_due_monotonic_ns: int
    cadence_seconds: float
    tolerance_seconds: float


@dataclass(frozen=True, slots=True)
class CompletedSample:
    schedule: ScheduledSample
    started_monotonic_ns: int
    completed_monotonic_ns: int
    lateness_seconds: float


@dataclass(frozen=True, slots=True)
class SafeStructureDescriptor:
    json_parse_success: bool
    root_json_type: str
    top_level_keys: tuple[str, ...]
    nested_paths_present: tuple[str, ...]
    field_types: tuple[tuple[str, str], ...]
    normalized_public_values: tuple[tuple[str, str], ...]
    parser_branch_id: str
    structural_digest: str


@dataclass(frozen=True, slots=True)
class SafeHttpResult:
    route: str
    transport: SampleTransport
    numeric_http_status: int | None
    latency_seconds: float
    response_bytes: int
    content_type: str | None
    safe_api_code: str | None = None
    runtime_classification: RuntimeHealthClassification = RuntimeHealthClassification.UNKNOWN
    classification_reason_code: ClassificationReasonCode = ClassificationReasonCode.NOT_APPLICABLE
    classifier_branch_id: str = "CLASSIFIER_NOT_APPLICABLE"
    safe_structure_descriptor: SafeStructureDescriptor | None = None
    sample_sequence_id: int | None = None
    sample_phase: PhaseName | None = None
    sample_utc: str | None = None
    analysis_timestamp_ms: int | None = None
    analysis_run_id: str | None = None

    @property
    def runtime_health(self) -> RuntimeHealthClassification:
        """Compatibility name retained for the tracked observer aggregation."""

        return self.runtime_classification


@dataclass(frozen=True, slots=True)
class ScheduleValidation:
    missed_scheduled_samples: tuple[int, ...] = ()
    unexplained_sequence_gaps: tuple[tuple[int, int], ...] = ()
    excessive_lateness_samples: tuple[int, ...] = ()
    max_normal_lateness_seconds: float = 0.0
    max_boundary_lateness_seconds: float = 0.0

    @property
    def accepted(self) -> bool:
        return not (
            self.missed_scheduled_samples
            or self.unexplained_sequence_gaps
            or self.excessive_lateness_samples
        )


@dataclass(slots=True)
class ObservationAggregates:
    first_completed_monotonic_ns: int | None = None
    last_completed_monotonic_ns: int | None = None
    completed_samples: list[CompletedSample] = field(default_factory=list)
    http_results: list[SafeHttpResult] = field(default_factory=list)
    client_smokes: dict[str, str] = field(default_factory=dict)
    observer_restarts: int = 0
    partial_windows_concatenated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        if (
            self.first_completed_monotonic_ns is None
            or self.last_completed_monotonic_ns is None
        ):
            return 0.0
        return (
            self.last_completed_monotonic_ns - self.first_completed_monotonic_ns
        ) / 1_000_000_000
