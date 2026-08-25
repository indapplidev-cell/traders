"""Verify the production shared-DB password binding without rendering it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BINDING = ROOT / ".secrets.production.local" / "shared-db-password"
GITIGNORE_RULE = "/.secrets.production.local/"
DOCKERIGNORE_RULE = ".secrets.production.local"


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=False, capture_output=True
    )


def _acl_restricted(path: Path) -> bool:
    literal = str(path.resolve()).replace("'", "''")
    command = rf"""
$ErrorActionPreference='Stop'
$current=([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value
$allowed=@($current,'S-1-5-18','S-1-5-32-544')
$acl=Get-Acl -LiteralPath '{literal}'
$rules=@($acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]))
$broad=@('S-1-1-0','S-1-5-11','S-1-5-32-545','S-1-5-32-546','S-1-5-7','S-1-5-20')
$broadCount=@($rules|Where-Object {{$broad -contains $_.IdentityReference.Value}}).Count
$unexpectedCount=@($rules|Where-Object {{$allowed -notcontains $_.IdentityReference.Value}}).Count
$denyCount=@($rules|Where-Object {{$_.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow}}).Count
$currentCount=@($rules|Where-Object {{$_.IdentityReference.Value -eq $current}}).Count
$systemCount=@($rules|Where-Object {{$_.IdentityReference.Value -eq 'S-1-5-18'}}).Count
$adminCount=@($rules|Where-Object {{$_.IdentityReference.Value -eq 'S-1-5-32-544'}}).Count
$ok=($acl.AreAccessRulesProtected -and $broadCount -eq 0 -and $unexpectedCount -eq 0 -and $denyCount -eq 0 -and $currentCount -gt 0 -and $systemCount -gt 0 -and $adminCount -gt 0)
if($ok){{'PASS'}}else{{'FAIL'}}
"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    return result.returncode == 0 and result.stdout.strip() == "PASS"


def binding_errors(path: Path = BINDING) -> tuple[str, ...]:
    errors: list[str] = []
    if not path.is_file():
        return ("BINDING_FILE_MISSING",)
    try:
        value = path.read_bytes()
        acl_restricted = _acl_restricted(path)
        gitignore = {
            line.strip()
            for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        }
        dockerignore = {
            line.strip()
            for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        }
    except (OSError, RuntimeError, UnicodeError, ValueError):
        return ("SAFE_INSPECTION_FAILED",)
    token = value.rstrip(b"\r\n")
    if len(token) < 48 or any(
        byte not in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        for byte in token
    ):
        errors.append("CREDENTIAL_FORMAT_INVALID")
    if value not in {token, token + b"\n", token + b"\r\n"}:
        errors.append("CREDENTIAL_FILE_CONTENT_INVALID")
    if not acl_restricted:
        errors.append("ACL_CONTRACT_FAILED")
    if GITIGNORE_RULE not in gitignore:
        errors.append("GIT_IGNORE_CONTRACT_FAILED")
    if DOCKERIGNORE_RULE not in dockerignore:
        errors.append("DOCKER_CONTEXT_EXCLUSION_FAILED")
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    if _git("check-ignore", "-q", "--", relative).returncode != 0:
        errors.append("BINDING_NOT_IGNORED")
    if _git("ls-files", "--error-unmatch", "--", relative).returncode == 0:
        errors.append("BINDING_TRACKED")
    return tuple(errors)


def main() -> int:
    errors = binding_errors()
    print(f"BINDING_FILE_PRESENT={'YES' if BINDING.is_file() else 'NO'}")
    print(f"BINDING_PROVISIONED={'YES' if BINDING.is_file() and not errors else 'NO'}")
    print(f"ACL_RESTRICTED={'YES' if BINDING.is_file() and 'ACL_CONTRACT_FAILED' not in errors else 'NO'}")
    print(f"GIT_IGNORED={'YES' if 'BINDING_NOT_IGNORED' not in errors and 'GIT_IGNORE_CONTRACT_FAILED' not in errors else 'NO'}")
    print(f"GIT_TRACKED={'YES' if 'BINDING_TRACKED' in errors else 'NO'}")
    print(f"DOCKER_CONTEXT_EXCLUDED={'YES' if 'DOCKER_CONTEXT_EXCLUSION_FAILED' not in errors else 'NO'}")
    print("SECRET_VALUE_OUTPUT=NO")
    print("SECRET_DERIVED_HASH_CREATED=NO")
    for error in errors:
        print(f"ERROR_CODE={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
