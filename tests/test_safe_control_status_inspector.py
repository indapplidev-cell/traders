from __future__ import annotations

from pathlib import Path


def test_control_status_inspector_is_get_only_and_no_echo() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "safe_control_status_inspector.py"
    ).read_text(encoding="utf-8")
    assert 'method="GET"' in source
    assert 'method="POST"' not in source
    assert "print(token" not in source
    assert "SECRET_VALUE_OUTPUT=NO" in source
    assert "ALLOWED_FIELDS" in source
