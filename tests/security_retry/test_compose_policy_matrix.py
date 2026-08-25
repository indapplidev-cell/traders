from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from scripts.security_retry_controls import (
    POSTGRES_PASSWORD_KEY_PATH,
    PolicyResult,
    ValueClass,
    binding_consistency,
    classify_tracked_value,
    inspect_tracked_compose_key,
    parse_indented_yaml_scalars,
    resolve_required_reference,
    tracked_compose_policy,
)


SENSITIVE_KEYS = (
    "services.db.environment.PASSWORD",
    "services.db.environment.PASSWD",
    "services.db.environment.PWD",
    "services.app.environment.CLIENT_SECRET",
    "services.app.environment.ACCESS_TOKEN",
    "services.app.environment.API_KEY",
    "services.app.environment.APIKEY",
    "services.app.environment.ACCESS_KEY",
    "services.app.environment.PRIVATE_KEY",
    "services.postgres.environment.POSTGRES_PASSWORD",
)
FAKE_VALUES = (
    "synthetic-credential",
    "quoted synthetic credential",
    "unicode-\u2603-\u043f\u0440\u0438\u043c\u0435\u0440",
    "line-one\\nline-two",
    "shell-$()",
    "shell-`command`",
    "punctuation-!@#$%^&*()",
    "x" * 4096,
)
REQUIRED_REFERENCES = tuple(
    f"${{{name}:?required}}"
    for name in (
        "DB_PASSWORD",
        "CLIENT_SECRET",
        "ACCESS_TOKEN",
        "API_KEY",
        "ACCESS_KEY",
        "PRIVATE_KEY",
        "POSTGRES_PASSWORD",
        "TRADERS_ML_POSTGRES_PASSWORD",
    )
)


def _synthetic_url(
    scheme: str,
    password: str | None,
    *,
    encoded: bool = False,
) -> str:
    credential = "synthetic"
    if password is not None:
        credential += ":" + password
    suffix = "%20value" if encoded else ""
    return scheme + "://" + credential + suffix + "@db/name"


@pytest.mark.parametrize(
    ("key_path", "value"),
    tuple(itertools.product(SENSITIVE_KEYS, FAKE_VALUES)),
)
def test_literal_sensitive_values_fail_without_echo(key_path: str, value: str) -> None:
    value_class = classify_tracked_value(key_path, value)
    assert value_class is ValueClass.LITERAL_SECRET

    text = f"services:\n  db:\n    environment:\n      PASSWORD: {value!r}\n"
    findings = tracked_compose_policy(
        Path("compose.yaml"),
        text_reader=lambda _path: text,
    )
    rendered = "\n".join(item.render() for item in findings)
    assert value not in rendered
    assert all(item.policy_result is PolicyResult.FAIL for item in findings)


@pytest.mark.parametrize(
    ("key_path", "value"),
    tuple(itertools.product(SENSITIVE_KEYS, REQUIRED_REFERENCES)),
)
def test_required_references_pass_without_value_output(
    key_path: str,
    value: str,
) -> None:
    assert classify_tracked_value(key_path, value) is ValueClass.REQUIRED_ENV_REFERENCE


@pytest.mark.parametrize(
    "value",
    (
        "${VALUE:-fallback}",
        "${VALUE-fallback}",
        "${VALUE:=fallback}",
        "${VALUE=fallback}",
        "${VALUE}",
        _synthetic_url("postgresql", "credential"),
        _synthetic_url("https", "credential"),
        _synthetic_url("redis", "credential"),
    ),
)
@pytest.mark.parametrize("key_path", SENSITIVE_KEYS[:5])
def test_defaults_optional_references_and_credential_urls_fail(
    key_path: str,
    value: str,
) -> None:
    value_class = classify_tracked_value(key_path, value)
    assert value_class in {
        ValueClass.ENV_REFERENCE_WITH_DEFAULT,
        ValueClass.ENV_REFERENCE_NOT_REQUIRED,
        ValueClass.CREDENTIAL_BEARING_URL,
    }


@pytest.mark.parametrize("name", tuple(f"REQUIRED_VALUE_{index}" for index in range(32)))
def test_missing_required_value_fails_closed(name: str) -> None:
    reference = f"${{{name}:?required}}"
    missing = resolve_required_reference(reference, {})
    empty = resolve_required_reference(reference, {name: ""})
    present = resolve_required_reference(reference, {name: "synthetic-value"})
    assert not missing.prepared
    assert missing.error_class == "REQUIRED_VALUE_MISSING"
    assert not empty.prepared
    assert present.prepared
    assert "synthetic-value" not in present.render()


@pytest.mark.parametrize(
    "malformed",
    (
        "\tkey: value",
        " key: value",
        "missing-separator",
        "sequence-without-assignment",
        "[]",
        "- =value",
        ": empty-key",
        "key:\n   child: value",
    ),
)
def test_parser_errors_never_include_raw_nodes(malformed: str) -> None:
    parsed = parse_indented_yaml_scalars(malformed, file="compose.yaml")
    assert parsed.errors
    rendered = "\n".join(error.render() for error in parsed.errors)
    assert malformed not in rendered
    assert "value=" not in rendered


@pytest.mark.parametrize(
    ("database_url", "password", "expected"),
    (
        (_synthetic_url("postgresql", "synthetic"), "synthetic", True),
        (_synthetic_url("postgresql", "synthetic", encoded=True), "synthetic value", True),
        (_synthetic_url("postgresql", "other"), "synthetic", False),
        (_synthetic_url("postgresql", None), "synthetic", False),
        ("not-a-url", "synthetic", False),
        (None, "synthetic", False),
        (_synthetic_url("postgresql", "synthetic"), None, False),
        ("", "", False),
    ),
)
def test_binding_consistency_is_boolean_only(
    database_url: str | None,
    password: str | None,
    expected: bool,
) -> None:
    result = binding_consistency(database_url, password)
    assert result.database_url_consistent is expected
    rendered = result.render()
    for candidate in (database_url, password):
        if candidate:
            assert candidate not in rendered


def test_actual_tracked_compose_has_required_reference() -> None:
    inspection = inspect_tracked_compose_key(
        Path("docker-compose.yml"),
        POSTGRES_PASSWORD_KEY_PATH,
    )
    assert inspection.file_exists
    assert inspection.key_exists
    assert inspection.value_class is ValueClass.APPROVED_EXTERNAL_SECRET_REFERENCE
    assert inspection.policy_result is PolicyResult.PASS


def test_actual_tracked_compose_policy_has_no_failures() -> None:
    findings = tracked_compose_policy(Path("docker-compose.yml"))
    assert all(
        getattr(item, "policy_result", PolicyResult.FAIL) is PolicyResult.PASS
        for item in findings
    )
