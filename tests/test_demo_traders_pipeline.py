from __future__ import annotations

from scripts.demo_traders_pipeline import StepResult, extract_session_id


def test_extract_session_id_with_equals() -> None:
    assert extract_session_id("session id = 12") == 12


def test_extract_session_id_with_colon() -> None:
    assert extract_session_id("session id: 12") == 12


def test_extract_session_id_with_runner_prefix() -> None:
    assert extract_session_id("Runner session id: 12") == 12


def test_extract_session_id_with_table_separator() -> None:
    assert extract_session_id("session id      | 12") == 12


def test_extract_session_id_returns_none_when_missing() -> None:
    assert extract_session_id("no id here") is None


def test_step_result_ok_property() -> None:
    ok_result = StepResult("ok", ["python"], 0, "", "")
    bad_result = StepResult("bad", ["python"], 1, "", "error")

    assert ok_result.ok is True
    assert bad_result.ok is False
