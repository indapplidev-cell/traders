from scripts.demo_traders_pipeline import StepResult, extract_session_id


def test_extract_session_id_from_equals_format() -> None:
    assert extract_session_id("session id = 12") == 12


def test_extract_session_id_from_colon_format() -> None:
    assert extract_session_id("session id: 12") == 12


def test_extract_session_id_from_runner_format() -> None:
    assert extract_session_id("Runner session id: 12") == 12


def test_extract_session_id_from_id_format() -> None:
    assert extract_session_id("id = 12") == 12


def test_extract_session_id_from_table_format() -> None:
    assert extract_session_id("session id      | 12") == 12


def test_extract_session_id_returns_none_when_missing() -> None:
    assert extract_session_id("no id here") is None


def test_step_result_ok_true() -> None:
    result = StepResult(
        title="Проверка",
        command=["python", "-m", "app.cli.commands", "health"],
        returncode=0,
        stdout="ok",
        stderr="",
    )

    assert result.ok is True


def test_step_result_ok_false() -> None:
    result = StepResult(
        title="Проверка",
        command=["python", "-m", "app.cli.commands", "health"],
        returncode=1,
        stdout="",
        stderr="error",
    )

    assert result.ok is False
