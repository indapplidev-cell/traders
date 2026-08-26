from pathlib import Path


def test_ack_inspector_never_renders_command_line_or_environment() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "safe_wal_ack_inspector.py"
    ).read_text(encoding="utf-8")
    assert "print(command" not in source
    assert "print(payload" not in source
    assert "COMMAND_LINE_VALUE_OUTPUT=NO" in source
    assert "SECRET_VALUE_OUTPUT=NO" in source
