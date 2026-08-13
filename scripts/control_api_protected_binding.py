"""Create the control capability inside the protected host boundary.

The command intentionally emits no stdout/stderr and never accepts or returns
credential material.
"""

from __future__ import annotations

import os
import secrets
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".control-api.token"
ACL_TEMPLATE = ROOT / ".env.production.local"


def _copy_acl(source: Path, target: Path) -> None:
    if os.name != "nt":
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        return
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    powershell = Path(system_root) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    command = (
        "$a=Get-Acl -LiteralPath $env:ACL_SOURCE; "
        "Set-Acl -LiteralPath $env:ACL_TARGET -AclObject $a"
    )
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command", command],
        env={"SystemRoot": system_root, "ACL_SOURCE": str(source), "ACL_TARGET": str(target)},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
    )
    if result.returncode:
        raise RuntimeError("CONTROL_CREDENTIAL_ACL_FAILED")


def ensure() -> None:
    if TARGET.is_file():
        return
    if not ACL_TEMPLATE.is_file():
        raise RuntimeError("CONTROL_CREDENTIAL_PROTECTED_FOUNDATION_MISSING")
    temporary = TARGET.with_name(f".{TARGET.name}.pending")
    try:
        with temporary.open("xb") as stream:
            stream.write(secrets.token_urlsafe(48).encode("ascii"))
            stream.write(b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        _copy_acl(ACL_TEMPLATE, temporary)
        os.replace(temporary, TARGET)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    try:
        ensure()
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
