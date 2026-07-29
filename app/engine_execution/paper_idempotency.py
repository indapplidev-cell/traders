"""Versioned PAPER identities over explicit public causal tuples only."""

from __future__ import annotations

from hashlib import sha256

from app.engine_safety.paper_domain import (
    PaperEventType,
    PaperExitCause,
    PaperReasonCode,
    fail,
    normalize_symbol,
    require_enum,
    require_identity,
    require_nonnegative_int,
)


PAPER_IDEMPOTENCY_VERSION = "v1"


def _key(kind: str, *parts: object) -> str:
    normalized: list[str] = []
    for index, part in enumerate(parts):
        value = getattr(part, "value", part)
        if value is None or not str(value).strip():
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "blank causal identity",
                f"parts[{index}]",
            )
        text = str(value).strip()
        if len(text) > 128 or not text.isascii():
            fail(
                PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
                "unbounded causal identity",
                f"parts[{index}]",
            )
        normalized.append(text)
    canonical = "|".join(f"{len(value)}:{value}" for value in normalized)
    digest = sha256(canonical.encode("ascii")).hexdigest()
    return f"paper:{kind}:{PAPER_IDEMPOTENCY_VERSION}:{digest}"


def command_idempotency_key(
    *,
    pipeline_run_id: str,
    analysis_result_id: str,
    setup_id: str,
    strategy_decision_id: str,
    risk_decision_id: str,
    symbol: str,
    side: object,
    closed_until_ms: int,
    configuration_fingerprint: str,
) -> str:
    return _key(
        "command",
        require_identity(pipeline_run_id, "pipeline_run_id"),
        require_identity(analysis_result_id, "analysis_result_id"),
        require_identity(setup_id, "setup_id"),
        require_identity(strategy_decision_id, "strategy_decision_id"),
        require_identity(risk_decision_id, "risk_decision_id"),
        normalize_symbol(symbol),
        side,
        require_nonnegative_int(closed_until_ms, "closed_until_ms"),
        require_identity(configuration_fingerprint, "configuration_fingerprint"),
    )


def order_idempotency_key(command_id: str, role: str) -> str:
    return _key(
        "order",
        require_identity(command_id, "command_id"),
        require_identity(role, "role"),
    )


def fill_idempotency_key(order_id: str, role: str) -> str:
    return _key(
        "fill",
        require_identity(order_id, "order_id"),
        require_identity(role, "role"),
    )


def position_application_key(fill_id: str) -> str:
    return _key("position-application", require_identity(fill_id, "fill_id"))


def exit_decision_idempotency_key(
    position_id: str,
    position_version: int,
    cause: PaperExitCause,
) -> str:
    if isinstance(position_version, bool) or not isinstance(position_version, int):
        fail(
            PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
            "invalid position version",
            "position_version",
        )
    if position_version < 0:
        fail(
            PaperReasonCode.PAPER_IDEMPOTENCY_KEY_INVALID,
            "invalid position version",
            "position_version",
        )
    return _key(
        "exit",
        require_identity(position_id, "position_id"),
        position_version,
        require_enum(
            cause,
            PaperExitCause,
            PaperReasonCode.PAPER_EXIT_CAUSE_UNSUPPORTED,
            "cause",
        ),
    )


def journal_event_idempotency_key(
    *,
    aggregate_type: str,
    aggregate_id: str,
    causation_id: str,
    event_type: PaperEventType,
) -> str:
    return _key(
        "journal",
        require_identity(aggregate_type, "aggregate_type"),
        require_identity(aggregate_id, "aggregate_id"),
        require_identity(causation_id, "causation_id"),
        require_enum(
            event_type,
            PaperEventType,
            PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION,
            "event_type",
        ),
    )
