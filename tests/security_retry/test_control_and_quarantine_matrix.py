from __future__ import annotations

import itertools

import pytest

from app.db.postgres_auth_probe import PostgresAuthenticationProbe
from scripts.security_retry_controls import (
    classify_quarantine_path,
    validate_controlled_runtime_semantics,
    verify_credential_status,
)


ARCHITECTURE_NOTE = (
    "docs/architecture/paper_controlled_runtime_configuration_and_dry_run.md"
)
ALLOWED_TEST_NAMES = tuple(
    f"tests/paper_controlled_runtime_canary/test_controlled_runtime_canary_{index}.py"
    for index in range(24)
)
ALLOWED_DOC_NAMES = tuple(
    f"docs/security/paper_controlled_runtime_canary_{index}.md"
    for index in range(12)
)
FORBIDDEN_NAMES = (
    "docker-compose.yml",
    ".env.production.local",
    "online_trader.md",
    "evidence/incident.md",
    "logs/canary.log",
    "data/canary.db",
    "venv/module.py",
    ".venv/module.py",
    "app/unrelated.py",
    "tests/test_unrelated.py",
    "docs/unrelated.md",
    "local/runtime.secret",
)


@pytest.mark.parametrize(
    "path",
    (
        "app/engine_paper/controlled_runtime.py",
        "app/engine_paper/controlled_runtime_canary.py",
        ARCHITECTURE_NOTE,
        *ALLOWED_TEST_NAMES,
        *ALLOWED_DOC_NAMES,
    ),
)
def test_corrected_quarantine_allowlist_accepts_only_narrow_paths(path: str) -> None:
    decision = classify_quarantine_path(path, architecture_note=ARCHITECTURE_NOTE)
    assert decision.allowed
    assert decision.allowlist_class != "UNEXPECTED"


@pytest.mark.parametrize("path", FORBIDDEN_NAMES)
def test_quarantine_forbidden_and_unrelated_paths_are_denied(path: str) -> None:
    decision = classify_quarantine_path(path, architecture_note=ARCHITECTURE_NOTE)
    assert not decision.allowed


def _probe(connection: str, sqlstate: str | None) -> PostgresAuthenticationProbe:
    return PostgresAuthenticationProbe(connection=connection, sqlstate=sqlstate)


@pytest.mark.parametrize("success_attempt", (1, 2, 3))
@pytest.mark.parametrize("noise", tuple(range(12)))
def test_credential_gate_uses_fresh_bounded_attempts(
    success_attempt: int,
    noise: int,
) -> None:
    del noise
    old_calls = 0

    def probe(password: str) -> PostgresAuthenticationProbe:
        nonlocal old_calls
        if password == "old-synthetic":
            old_calls += 1
            if old_calls < success_attempt:
                raise TimeoutError("synthetic-value-that-must-not-render")
            return _probe("DENIED", "28P01")
        return _probe("CONNECTED", None)

    result = verify_credential_status(
        old_password="old-synthetic",
        new_password="new-synthetic",
        probe=probe,
        max_attempts=3,
    )
    assert result.old_invalidated == "YES"
    assert result.new_valid == "YES"
    assert result.repeat_rotation == "NO"
    assert result.attempts == success_attempt
    rendered = result.render()
    assert "old-synthetic" not in rendered
    assert "new-synthetic" not in rendered


@pytest.mark.parametrize("noise", tuple(range(16)))
def test_active_old_credential_requires_exactly_one_rotation_decision(noise: int) -> None:
    del noise

    def probe(password: str) -> PostgresAuthenticationProbe:
        if password == "old-synthetic":
            return _probe("CONNECTED", None)
        return _probe("CONNECTED", None)

    result = verify_credential_status(
        old_password="old-synthetic",
        new_password="new-synthetic",
        probe=probe,
    )
    assert result.old_invalidated == "NO"
    assert result.repeat_rotation == "YES"


@pytest.mark.parametrize("max_attempts", (0, 4, 5, 10))
def test_credential_gate_rejects_unbounded_attempt_counts(max_attempts: int) -> None:
    result = verify_credential_status(
        old_password="old-synthetic",
        new_password="new-synthetic",
        probe=lambda _password: _probe("CONNECTED", None),
        max_attempts=max_attempts,
    )
    assert result.attempts == 0
    assert result.repeat_rotation == "NO_DECISION"


BASELINE = """
from enum import Enum
class PaperControlledRuntimeAction(Enum):
    VALIDATE = "VALIDATE"
class PaperDatabaseAccessMode(Enum):
    READ_ONLY = "READ_ONLY"
def evaluate_controlled_runtime_startup_gate(action, access):
    return action, access
"""
CANDIDATE = """
from enum import Enum
class PaperControlledRuntimeAction(Enum):
    VALIDATE = "VALIDATE"
    SINGLE_CYCLE_CANARY = "SINGLE_CYCLE_CANARY"
class PaperDatabaseAccessMode(Enum):
    READ_ONLY = "READ_ONLY"
    ISOLATED_CANARY_READ_WRITE = "ISOLATED_CANARY_READ_WRITE"
def evaluate_controlled_runtime_startup_gate(action, access):
    expected_access = PaperDatabaseAccessMode.ISOLATED_CANARY_READ_WRITE
    if action is PaperControlledRuntimeAction.SINGLE_CYCLE_CANARY:
        return action, expected_access
    return action, access
"""


@pytest.mark.parametrize("repeat", tuple(range(24)))
def test_controlled_runtime_semantic_gate_accepts_canary_only_wiring(repeat: int) -> None:
    del repeat
    result = validate_controlled_runtime_semantics(BASELINE, CANDIDATE)
    assert result.passed
    assert result.canary_only_wiring
    assert not result.production_denial_weakened
    assert not result.live_denial_weakened
    assert not result.safe_defaults_changed
    assert result.secret_literals_found == 0
    assert not result.protected_binding_access_added
    assert result.non_canary_semantic_changes == 0


@pytest.mark.parametrize(
    "injection",
    (
        "\ndef production_enable(): return True\n",
        "\nDATABASE_URL = 'synthetic'\n",
        "\nTRADERS_ML_POSTGRES_PASSWORD = 'synthetic'\n",
        "\ndef daemon(): return None\n",
        "\ndef scheduler(): return None\n",
        "\ndef network_fetch(): return None\n",
        "\nclass Other: pass\n",
        "\ndef live_enable(): return True\n",
    ),
)
def test_controlled_runtime_semantic_gate_rejects_non_canary_changes(
    injection: str,
) -> None:
    result = validate_controlled_runtime_semantics(BASELINE, CANDIDATE + injection)
    assert not result.passed
