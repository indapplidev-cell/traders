from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest

from app.engine_paper.exit_evaluation_cursor import (
    MAX_EXIT_EVALUATION_WINDOW_CANDLES,
    PaperExitCursorAdvance,
    advanced_cursor,
    paper_exit_cursor_window_identity,
)
from app.engine_safety import ExecutionMode


def _unsafe_replace(value, **changes):
    clone = object.__new__(type(value))
    for field in type(value).__dataclass_fields__:
        object.__setattr__(
            clone, field, changes.get(field, getattr(value, field))
        )
    return clone


def _assert_rejected(call):
    try:
        call()
    except BaseException:
        return
    raise AssertionError("invalid contract material was accepted")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cursor_id", ""),
        ("contract_version", "V2"),
        ("position_id", ""),
        ("mode", ExecutionMode.OFF),
        ("mode", ExecutionMode.LIVE),
        ("symbol", ""),
        ("last_evaluated_closed_until_ms", -1),
        ("last_evaluated_closed_until_ms", True),
        ("last_evaluated_closed_until_ms", 1),
        ("position_opened_closed_until_ms", -1),
        ("position_opened_closed_until_ms", True),
        ("position_opened_closed_until_ms", 1),
        ("evaluation_policy_id", ""),
        ("version", -1),
        ("version", True),
        ("correlation_id", ""),
        ("causation_id", ""),
    ],
)
def test_cursor_contract_rejects_invalid_fields(cursor_factory, field, value):
    cursor = cursor_factory()
    _assert_rejected(lambda: replace(cursor, **{field: value}))


def test_cursor_rejects_boundary_before_position_open(cursor_factory):
    cursor = cursor_factory()
    with pytest.raises(ValueError, match="aligned and monotonic"):
        replace(
            cursor,
            last_evaluated_closed_until_ms=(
                cursor.position_opened_closed_until_ms - 60_000
            ),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("last_advance_idempotency_key", "advance:key"),
        ("last_advance_from_closed_until_ms", 1),
        ("last_advance_to_closed_until_ms", 2),
        ("last_advance_expected_version", 0),
        ("last_window_identity", "window:key"),
    ],
)
def test_cursor_last_advance_metadata_is_all_or_none(cursor_factory, field, value):
    with pytest.raises(ValueError, match="must be complete"):
        cursor_factory(**{field: value})


@pytest.mark.parametrize("count", range(1, MAX_EXIT_EVALUATION_WINDOW_CANDLES + 1))
def test_every_bounded_window_size_advances_exactly_once(
    cursor_factory, advance_factory, count
):
    cursor = cursor_factory()
    advance = advance_factory(cursor, count)
    changed = advanced_cursor(cursor, advance)
    assert changed.version == 1
    assert (
        changed.last_evaluated_closed_until_ms
        == cursor.last_evaluated_closed_until_ms + count * 60_000
    )
    assert changed.last_advance_idempotency_key == advance.idempotency_key


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        ("position", "position mismatch"),
        ("policy", "policy mismatch"),
        ("version", "version mismatch"),
        ("from", "start mismatch"),
        ("regression", "must be monotonic"),
    ],
)
def test_advanced_cursor_rejects_graph_conflicts(
    cursor_factory, advance_factory, mutation, expected_message
):
    cursor = cursor_factory()
    advance = advance_factory(cursor, 1)
    if mutation == "position":
        advance = _unsafe_replace(advance, position_id="position:other")
    elif mutation == "policy":
        advance = _unsafe_replace(advance, evaluation_policy_id="policy:other")
    elif mutation == "version":
        advance = _unsafe_replace(advance, expected_version=1)
    elif mutation == "from":
        advance = _unsafe_replace(
            advance,
            from_closed_until_ms=cursor.last_evaluated_closed_until_ms + 60_000,
        )
    else:
        advance = _unsafe_replace(
            advance,
            to_closed_until_ms=cursor.last_evaluated_closed_until_ms,
        )
    with pytest.raises(ValueError, match=expected_message):
        advanced_cursor(cursor, advance)


@pytest.mark.parametrize(
    ("boundaries", "to_delta"),
    [
        ((120_000,), 120_000),
        ((60_000, 180_000), 180_000),
        ((60_000, 60_000), 60_000),
        ((0,), 0),
        ((-60_000,), -60_000),
    ],
)
def test_advance_contract_rejects_gap_duplicate_or_regression(
    cursor_factory, boundaries, to_delta
):
    cursor = cursor_factory()
    absolute = tuple(
        cursor.last_evaluated_closed_until_ms + delta for delta in boundaries
    )
    end = cursor.last_evaluated_closed_until_ms + to_delta
    identity = paper_exit_cursor_window_identity(
        position_id=cursor.position_id,
        expected_version=cursor.version,
        from_boundary_ms=cursor.last_evaluated_closed_until_ms,
        to_boundary_ms=max(0, end),
        evaluation_policy_id=cursor.evaluation_policy_id,
        evaluated_close_boundaries_ms=absolute,
    )
    with pytest.raises(ValueError):
        PaperExitCursorAdvance(
            position_id=cursor.position_id,
            expected_version=cursor.version,
            from_closed_until_ms=cursor.last_evaluated_closed_until_ms,
            to_closed_until_ms=end,
            evaluation_policy_id=cursor.evaluation_policy_id,
            evaluated_close_boundaries_ms=absolute,
            idempotency_key=identity,
            window_identity=identity,
            advanced_at=cursor.updated_at + timedelta(minutes=3),
            correlation_id=cursor.correlation_id,
            causation_id="causation:gap",
        )


@pytest.mark.parametrize("field", ["idempotency_key", "window_identity"])
def test_advance_identity_is_not_caller_overridable(
    cursor_factory, advance_factory, field
):
    cursor = cursor_factory()
    advance = advance_factory(cursor, 2)
    with pytest.raises(ValueError, match="identity"):
        replace(advance, **{field: "paper:exit-cursor-advance:v1:conflict"})


def test_long_lived_position_uses_bounded_windows_without_reread(
    cursor_factory, advance_factory
):
    cursor = cursor_factory()
    remaining = 10_000
    windows = 0
    initial = cursor.last_evaluated_closed_until_ms
    while remaining:
        size = min(64, remaining)
        advance = advance_factory(cursor, size)
        assert len(advance.evaluated_close_boundaries_ms) <= 64
        cursor = advanced_cursor(cursor, advance)
        remaining -= size
        windows += 1
    assert windows == 157
    assert cursor.version == 157
    assert cursor.last_evaluated_closed_until_ms == initial + 10_000 * 60_000


@pytest.mark.parametrize("sequence", [(1, 1), (2, 3), (64, 64), (7, 11), (63, 1)])
def test_multiple_sequential_windows_never_skip(
    cursor_factory, advance_factory, sequence
):
    cursor = cursor_factory()
    initial = cursor.last_evaluated_closed_until_ms
    for count in sequence:
        cursor = advanced_cursor(cursor, advance_factory(cursor, count))
    assert cursor.version == len(sequence)
    assert cursor.last_evaluated_closed_until_ms == initial + sum(sequence) * 60_000
