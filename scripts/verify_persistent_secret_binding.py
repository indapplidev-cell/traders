"""Verify the local persistent readonly-API secret binding without exposing it."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BINDING = ROOT / ".env.production.local"
GITIGNORE_RULE = "/.env.production.local"
DOCKERIGNORE_RULE = ".env.production.local"
DATABASE_KEY = "TRADERS_READONLY_API_DATABASE_URL"
HOST_KEY = "TRADERS_READONLY_API_HOST"
PORT_KEY = "TRADERS_READONLY_API_PORT"
REQUIRED_KEYS = (DATABASE_KEY, HOST_KEY, PORT_KEY)


@dataclass(frozen=True)
class ParsedBinding:
    values: Mapping[str, str]
    duplicate_keys: tuple[str, ...]


@dataclass(frozen=True)
class AclState:
    inheritance_disabled: bool
    current_user_sid: str
    current_user_allowed: bool
    system_allowed: bool
    administrators_allowed: bool
    broad_principals: int
    unexpected_principals: int
    deny_rules: int

    @property
    def restricted(self) -> bool:
        return (
            self.inheritance_disabled
            and self.current_user_allowed
            and self.system_allowed
            and self.administrators_allowed
            and self.broad_principals == 0
            and self.unexpected_principals == 0
            and self.deny_rules == 0
        )


def parse_binding_text(text: str) -> ParsedBinding:
    values: dict[str, str] = {}
    duplicates: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values and key not in duplicates:
            duplicates.append(key)
        values[key] = value.strip()
    return ParsedBinding(values=values, duplicate_keys=tuple(duplicates))


def contract_errors(
    parsed: ParsedBinding,
    *,
    git_ignored: bool,
    git_tracked: bool,
    docker_excluded: bool,
    acl: AclState,
    require_provisioned_secret: bool,
) -> tuple[str, ...]:
    errors: list[str] = []
    missing = [key for key in REQUIRED_KEYS if key not in parsed.values]
    if missing:
        errors.append("REQUIRED_KEYS_MISSING")
    if parsed.duplicate_keys:
        errors.append("DUPLICATE_KEYS")
    if parsed.values.get(HOST_KEY) != "127.0.0.1":
        errors.append("BIND_HOST_NOT_LOOPBACK")
    if parsed.values.get(PORT_KEY) != "8765":
        errors.append("PORT_NOT_8765")
    if require_provisioned_secret and not parsed.values.get(DATABASE_KEY, ""):
        errors.append("EMPTY_DATABASE_URL")
    if not git_ignored:
        errors.append("GIT_IGNORE_CONTRACT_FAILED")
    if git_tracked:
        errors.append("BINDING_FILE_TRACKED")
    if not docker_excluded:
        errors.append("DOCKER_CONTEXT_EXCLUSION_FAILED")
    if not acl.restricted:
        errors.append("ACL_CONTRACT_FAILED")
    return tuple(errors)


def _run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def git_state(path: Path) -> tuple[bool, bool]:
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return False, False
    ignored = _run_git("check-ignore", "-q", "--", relative).returncode == 0
    tracked = (
        _run_git("ls-files", "--error-unmatch", "--", relative).returncode == 0
    )
    return ignored, tracked


def docker_context_excluded() -> bool:
    rules = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return DOCKERIGNORE_RULE in rules


def _powershell_executable() -> str:
    for candidate in ("pwsh.exe", "pwsh", "powershell.exe", "powershell"):
        try:
            result = subprocess.run(
                [candidate, "-NoProfile", "-NonInteractive", "-Command", "$PSVersionTable.PSVersion.Major"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return candidate
    raise RuntimeError("PowerShell is required for the Windows ACL contract")


def inspect_windows_acl(path: Path) -> AclState:
    if os.name != "nt":
        raise RuntimeError("Windows ACL contract is unavailable on this platform")
    script = (
        "$a=Get-Acl -LiteralPath $env:ACL_TARGET;"
        "$s=([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value;"
        "[ordered]@{sddl=[string]$a.Sddl;protected=[bool]$a.AreAccessRulesProtected;"
        "current_sid=[string]$s}|ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        [
            _powershell_executable(),
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        env={**os.environ, "ACL_TARGET": str(path.resolve())},
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    if result.returncode != 0:
        raise RuntimeError("Windows ACL inspection failed")
    payload = json.loads(result.stdout.strip())
    sddl = str(payload["sddl"])
    current_sid = str(payload["current_sid"])
    identities = tuple(re.findall(r";;;([^\)]+)\)", sddl))
    allowed = {current_sid, "SY", "BA", "S-1-5-18", "S-1-5-32-544"}
    broad = {"WD", "AU", "BU", "BG", "AN", "NS", "S-1-1-0", "S-1-5-11"}
    return AclState(
        inheritance_disabled=bool(payload["protected"]),
        current_user_sid=current_sid,
        current_user_allowed=current_sid in identities,
        system_allowed=bool({"SY", "S-1-5-18"} & set(identities)),
        administrators_allowed=bool({"BA", "S-1-5-32-544"} & set(identities)),
        broad_principals=sum(identity in broad for identity in identities),
        unexpected_principals=sum(identity not in allowed for identity in identities),
        deny_rules=sddl.count("(D;"),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the persistent readonly-API binding without printing secrets."
    )
    parser.add_argument("--path", type=Path, default=CANONICAL_BINDING)
    parser.add_argument("--require-provisioned-secret", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path = args.path.resolve()
    if not path.is_file():
        print("BINDING_FILE_PRESENT=NO")
        print("SECRET_VALUE_OUTPUT=NO")
        print("ERROR_CODE=BINDING_FILE_MISSING")
        return 1

    try:
        parsed = parse_binding_text(path.read_text(encoding="utf-8"))
        git_ignored, git_tracked = git_state(path)
        docker_excluded = docker_context_excluded()
        acl = inspect_windows_acl(path)
    except (OSError, UnicodeError, ValueError, RuntimeError, json.JSONDecodeError):
        print("BINDING_FILE_PRESENT=YES")
        print("SECRET_VALUE_OUTPUT=NO")
        print("ERROR_CODE=SAFE_INSPECTION_FAILED")
        return 1

    missing_count = sum(key not in parsed.values for key in REQUIRED_KEYS)
    errors = contract_errors(
        parsed,
        git_ignored=git_ignored,
        git_tracked=git_tracked,
        docker_excluded=docker_excluded,
        acl=acl,
        require_provisioned_secret=args.require_provisioned_secret,
    )
    print("BINDING_FILE_PRESENT=YES")
    print(f"REQUIRED_KEY_NAMES={','.join(REQUIRED_KEYS)}")
    print(f"REQUIRED_KEYS_PRESENT={'YES' if missing_count == 0 else 'NO'}")
    print(f"DATABASE_URI_KEY_PRESENT={'YES' if DATABASE_KEY in parsed.values else 'NO'}")
    print(
        "DATABASE_URI_PROVISIONED="
        + ("YES" if bool(parsed.values.get(DATABASE_KEY, "")) else "NO")
    )
    print(
        "BIND_HOST="
        + ("127.0.0.1" if parsed.values.get(HOST_KEY) == "127.0.0.1" else "INVALID")
    )
    print("PORT=" + ("8765" if parsed.values.get(PORT_KEY) == "8765" else "INVALID"))
    print(f"DUPLICATE_KEYS={len(parsed.duplicate_keys)}")
    print(f"GIT_IGNORED={'YES' if git_ignored else 'NO'}")
    print(f"GIT_TRACKED={'YES' if git_tracked else 'NO'}")
    print(f"DOCKER_CONTEXT_EXCLUDED={'YES' if docker_excluded else 'NO'}")
    print(f"ACL_INHERITANCE_DISABLED={'YES' if acl.inheritance_disabled else 'NO'}")
    print(f"ACL_CURRENT_USER_SID={acl.current_user_sid}")
    print(f"ACL_CURRENT_USER_ALLOWED={'YES' if acl.current_user_allowed else 'NO'}")
    print(f"ACL_SYSTEM_ALLOWED={'YES' if acl.system_allowed else 'NO'}")
    print(
        "ACL_ADMINISTRATORS_ALLOWED="
        + ("YES" if acl.administrators_allowed else "NO")
    )
    print(f"ACL_BROAD_PRINCIPALS={acl.broad_principals}")
    print(f"ACL_UNEXPECTED_PRINCIPALS={acl.unexpected_principals}")
    print(f"ACL_RESTRICTED={'YES' if acl.restricted else 'NO'}")
    print("SECRET_VALUE_OUTPUT=NO")
    for error in errors:
        print(f"ERROR_CODE={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
