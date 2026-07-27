from pathlib import Path

from scripts.verify_persistent_secret_binding import (
    AclState,
    CANONICAL_BINDING,
    DATABASE_KEY,
    DOCKERIGNORE_RULE,
    GITIGNORE_RULE,
    HOST_KEY,
    PORT_KEY,
    ROOT,
    contract_errors,
    parse_binding_text,
)


VALID_TEXT = f"""\
{DATABASE_KEY}=
{HOST_KEY}=127.0.0.1
{PORT_KEY}=8765
"""


def restricted_acl(**overrides: object) -> AclState:
    values = {
        "inheritance_disabled": True,
        "current_user_sid": "S-1-5-21-test",
        "current_user_allowed": True,
        "system_allowed": True,
        "administrators_allowed": True,
        "broad_principals": 0,
        "unexpected_principals": 0,
        "deny_rules": 0,
    }
    values.update(overrides)
    return AclState(**values)


def assess(text: str, **overrides: object) -> tuple[str, ...]:
    inputs = {
        "git_ignored": True,
        "git_tracked": False,
        "docker_excluded": True,
        "acl": restricted_acl(),
        "require_provisioned_secret": False,
    }
    inputs.update(overrides)
    return contract_errors(parse_binding_text(text), **inputs)


def test_canonical_path_and_exact_exclusion_rules() -> None:
    assert CANONICAL_BINDING == ROOT / ".env.production.local"
    git_rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    docker_rules = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert GITIGNORE_RULE in git_rules
    assert DOCKERIGNORE_RULE in docker_rules


def test_env_example_uses_canonical_placeholders_only() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    section = text.split("# Persistent production Readonly API binding.", 1)[1]
    parsed = parse_binding_text(section)
    assert parsed.values == {
        DATABASE_KEY: "",
        HOST_KEY: "127.0.0.1",
        PORT_KEY: "8765",
    }
    assert "://" not in section
    assert "TRADERS_READONLY_API_DATABASE_URI" not in section
    assert "TRADERS_READONLY_API_BIND_HOST" not in section


def test_required_keys_and_foundation_empty_secret_are_accepted() -> None:
    parsed = parse_binding_text(VALID_TEXT)
    assert set(parsed.values) == {DATABASE_KEY, HOST_KEY, PORT_KEY}
    assert assess(VALID_TEXT) == ()


def test_duplicate_key_is_rejected() -> None:
    text = VALID_TEXT + f"{PORT_KEY}=8765\n"
    assert "DUPLICATE_KEYS" in assess(text)


def test_loopback_host_and_fixed_port_are_required() -> None:
    assert "BIND_HOST_NOT_LOOPBACK" in assess(
        VALID_TEXT.replace("127.0.0.1", "0.0.0.0")
    )
    assert "PORT_NOT_8765" in assess(VALID_TEXT.replace("8765", "8080"))


def test_require_provisioned_mode_rejects_empty_secret() -> None:
    assert "EMPTY_DATABASE_URL" in assess(
        VALID_TEXT, require_provisioned_secret=True
    )


def test_require_provisioned_mode_accepts_nonempty_secret_without_rendering_it() -> None:
    opaque = "runtime-only-sensitive-value"
    text = VALID_TEXT.replace(f"{DATABASE_KEY}=", f"{DATABASE_KEY}={opaque}")
    errors = assess(text, require_provisioned_secret=True)
    assert errors == ()
    assert opaque not in repr(errors)


def test_broad_acl_is_rejected() -> None:
    errors = assess(VALID_TEXT, acl=restricted_acl(broad_principals=1))
    assert "ACL_CONTRACT_FAILED" in errors


def test_tracked_file_is_rejected() -> None:
    assert "BINDING_FILE_TRACKED" in assess(VALID_TEXT, git_tracked=True)


def test_missing_git_or_docker_exclusion_is_rejected() -> None:
    assert "GIT_IGNORE_CONTRACT_FAILED" in assess(VALID_TEXT, git_ignored=False)
    assert "DOCKER_CONTEXT_EXCLUSION_FAILED" in assess(
        VALID_TEXT, docker_excluded=False
    )


def test_secret_value_never_appears_in_safe_contract_errors() -> None:
    secret = "do-not-" + "render-this-sensitive-value"
    text = VALID_TEXT.replace(f"{DATABASE_KEY}=", f"{DATABASE_KEY}={secret}")
    rendered = "\n".join(
        assess(text, git_tracked=True, require_provisioned_secret=True)
    )
    assert secret not in rendered
