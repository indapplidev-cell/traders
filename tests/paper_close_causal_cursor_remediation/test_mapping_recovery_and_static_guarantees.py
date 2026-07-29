from __future__ import annotations

import ast
from dataclasses import replace

import pytest

from app.db.paper_mappings import (
    orm_values_to_paper_exit_cursor,
    paper_exit_cursor_to_orm_values,
)
from app.engine_paper.exit_cursor_recovery import (
    PaperExitCursorRecoveryOutcome,
    recover_uncertain_cursor_commit,
)
from app.engine_paper.exit_evaluation_cursor import advanced_cursor


@pytest.mark.parametrize("window_size", range(1, 33))
def test_cursor_mapping_round_trip_preserves_every_field(
    cursor_factory, advance_factory, window_size
):
    cursor = cursor_factory()
    changed = advanced_cursor(cursor, advance_factory(cursor, window_size))
    values = paper_exit_cursor_to_orm_values(changed)
    assert orm_values_to_paper_exit_cursor(values) == changed
    assert len(values) == 18


class _FakeSession:
    def __init__(self, value=None, *, unavailable=False):
        self.value = value
        self.unavailable = unavailable

    def __enter__(self):
        if self.unavailable:
            raise RuntimeError("unavailable")
        return self

    def __exit__(self, *_):
        return False

    def get(self, model, key):
        if self.value is None:
            return None
        return type("Row", (), paper_exit_cursor_to_orm_values(self.value))()


class _Factory:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0
        self.sessions = []

    def __call__(self):
        value = self.values[min(self.calls, len(self.values) - 1)]
        self.calls += 1
        session = (
            _FakeSession(unavailable=True)
            if value == "UNAVAILABLE"
            else _FakeSession(value)
        )
        self.sessions.append(session)
        return session


@pytest.mark.parametrize("unavailable_prefix", [0, 1, 2])
def test_uncertain_cursor_recovery_committed_uses_fresh_sessions(
    cursor_factory, advance_factory, unavailable_prefix
):
    expected = advanced_cursor(
        cursor_factory(), advance_factory(cursor_factory(), 1)
    )
    factory = _Factory(["UNAVAILABLE"] * unavailable_prefix + [expected])
    result = recover_uncertain_cursor_commit(factory, expected)
    assert result.outcome is PaperExitCursorRecoveryOutcome.RESOLVED_COMMITTED
    assert result.attempts_used == unavailable_prefix + 1
    assert len({id(session) for session in factory.sessions}) == factory.calls


def test_uncertain_cursor_recovery_absent_is_bounded(cursor_factory):
    expected = cursor_factory()
    factory = _Factory([None, None, None])
    result = recover_uncertain_cursor_commit(factory, expected)
    assert result.outcome is PaperExitCursorRecoveryOutcome.RESOLVED_NOT_COMMITTED
    assert result.attempts_used == 3
    assert factory.calls == 3


def test_uncertain_cursor_recovery_conflict_is_not_replayed(cursor_factory):
    expected = cursor_factory()
    conflict = replace(expected, correlation_id="correlation:conflict")
    factory = _Factory([conflict])
    result = recover_uncertain_cursor_commit(factory, expected)
    assert result.outcome is PaperExitCursorRecoveryOutcome.IDEMPOTENCY_CONFLICT
    assert factory.calls == 1


def test_uncertain_cursor_recovery_unavailable_is_bounded(cursor_factory):
    expected = cursor_factory()
    factory = _Factory(["UNAVAILABLE", "UNAVAILABLE", "UNAVAILABLE"])
    result = recover_uncertain_cursor_commit(factory, expected)
    assert result.outcome is PaperExitCursorRecoveryOutcome.UNRESOLVED
    assert result.attempts_used == 3
    assert factory.calls == 3


@pytest.mark.parametrize("attempts", [0, -1, 4, 5])
def test_uncertain_cursor_recovery_rejects_unbounded_attempts(
    cursor_factory, attempts
):
    with pytest.raises(ValueError, match="between 1 and 3"):
        recover_uncertain_cursor_commit(_Factory([None]), cursor_factory(), attempts=attempts)


@pytest.mark.parametrize(
    ("path", "forbidden"),
    [
        ("app/engine_paper/fill_causal_boundary.py", "datetime.now"),
        ("app/engine_paper/fill_causal_boundary.py", "time.time"),
        ("app/engine_paper/fill_causal_boundary.py", "random."),
        ("app/engine_paper/fill_causal_boundary.py", "requests."),
        ("app/engine_paper/fill_causal_boundary.py", "Session("),
        ("app/engine_paper/fill_simulator.py", "datetime.now"),
        ("app/engine_paper/fill_simulator.py", "time.time"),
        ("app/engine_paper/fill_simulator.py", "random."),
        ("app/engine_paper/fill_simulator.py", "requests."),
        ("app/engine_paper/fill_simulator.py", "Session("),
        ("app/engine_paper/exit_evaluation_cursor.py", "datetime.now"),
        ("app/engine_paper/exit_evaluation_cursor.py", "time.time"),
        ("app/engine_paper/exit_evaluation_cursor.py", "random."),
        ("app/engine_paper/exit_evaluation_cursor.py", "requests."),
        ("app/engine_paper/exit_evaluation_cursor.py", "Session("),
    ],
)
def test_pure_authorities_have_no_impure_calls(path, forbidden):
    source = open(path, encoding="utf-8").read()
    assert forbidden not in source
    ast.parse(source)


@pytest.mark.parametrize(
    "path",
    [
        "app/engine_paper/fill_causal_boundary.py",
        "app/engine_paper/fill_simulator.py",
        "app/engine_paper/exit_evaluation_cursor.py",
        "app/engine_paper/exit_cursor_recovery.py",
        "app/db/paper_mappings.py",
    ],
)
def test_remediation_modules_have_no_float_literals(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
