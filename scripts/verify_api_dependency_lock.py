"""Verify the read-only API dependency lock contract using only the stdlib."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_LOCK = ROOT / "requirements" / "api-runtime.lock.txt"
DEV_LOCK = ROOT / "requirements" / "api-dev.lock.txt"
TOOL_LOCK = ROOT / "requirements" / "lock-tools.txt"
LOCK_FILES = (RUNTIME_LOCK, DEV_LOCK, TOOL_LOCK)

PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9,._-]+\])?)==([^\s;]+)")
HASH_RE = re.compile(r"--hash=sha256:[0-9a-f]{64}(?:\s|$)")
WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)(?:^|[\s\"'])[a-z]:[\\/]")
CREDENTIAL_RE = re.compile(r"(?i)https?://[^\s/@:]+:[^\s/@]+@")
FORBIDDEN_OPTIONS = (
    "--index-url",
    "--extra-index-url",
    "--find-links",
    "--trusted-host",
    "--editable",
    "-e ",
)
RUNTIME_FORBIDDEN_PACKAGES = frozenset(
    {"pytest", "pluggy", "iniconfig", "pygments", "pip-tools"}
)
REQUIRED_HEADER_FIELDS = (
    "# Source commit:",
    "# Target:",
    "# Generator:",
    "# Command:",
    "# Generated at UTC:",
)


def _logical_lines(text: str) -> list[str]:
    logical: list[str] = []
    current = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            current += stripped[:-1].rstrip() + " "
            continue
        current += stripped
        logical.append(current)
        current = ""
    if current:
        logical.append(current)
    return logical


def _canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _verify_lock(path: Path, require_source_header: bool) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    packages: dict[str, str] = {}
    if not path.is_file():
        return packages, [f"{path.relative_to(ROOT)}: missing"]

    raw = path.read_bytes()
    if b"\r" in raw:
        errors.append(f"{path.name}: line endings are not normalized LF")
    text = raw.decode("utf-8")
    lowered = text.lower()
    if WINDOWS_ABSOLUTE_RE.search(text) or "file://" in lowered:
        errors.append(f"{path.name}: absolute or file URL path found")
    if CREDENTIAL_RE.search(text):
        errors.append(f"{path.name}: credential-bearing URL found")
    if any(option in lowered for option in FORBIDDEN_OPTIONS):
        errors.append(f"{path.name}: uncontrolled source or editable entry found")
    if require_source_header:
        for field in REQUIRED_HEADER_FIELDS:
            if field not in text:
                errors.append(f"{path.name}: missing deterministic header field {field}")

    for line in _logical_lines(text):
        match = PIN_RE.match(line)
        if match is None:
            errors.append(f"{path.name}: installable line is not exactly pinned: {line!r}")
            continue
        name, version = match.groups()
        canonical = _canonical_name(name.split("[", 1)[0])
        if " @ " in line or version.startswith((".", "/", "\\")):
            errors.append(f"{path.name}: local/direct dependency entry found for {name}")
        if not HASH_RE.search(line):
            errors.append(f"{path.name}: SHA256 hash missing for {name}")
        if canonical in packages:
            errors.append(f"{path.name}: duplicate package {canonical}")
        packages[canonical] = version
    if not packages:
        errors.append(f"{path.name}: no installable packages")
    return packages, errors


def verify_contract() -> list[str]:
    errors: list[str] = []
    for path in LOCK_FILES:
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)}: missing")
    if errors:
        return errors

    runtime, runtime_errors = _verify_lock(RUNTIME_LOCK, require_source_header=True)
    dev, dev_errors = _verify_lock(DEV_LOCK, require_source_header=True)
    tools, tool_errors = _verify_lock(TOOL_LOCK, require_source_header=False)
    errors.extend(runtime_errors)
    errors.extend(dev_errors)
    errors.extend(tool_errors)

    if runtime.get("fastapi") != "0.116.1":
        errors.append("api-runtime.lock.txt: FastAPI must be exactly 0.116.1")
    if dev.get("fastapi") != "0.116.1":
        errors.append("api-dev.lock.txt: FastAPI must be exactly 0.116.1")
    if runtime.get("uvicorn") != "0.51.0":
        errors.append("api-runtime.lock.txt: Uvicorn must be exactly 0.51.0")
    if dev.get("uvicorn") != "0.51.0":
        errors.append("api-dev.lock.txt: Uvicorn must be exactly 0.51.0")
    unexpected_runtime = sorted(RUNTIME_FORBIDDEN_PACKAGES.intersection(runtime))
    if unexpected_runtime:
        errors.append(
            "api-runtime.lock.txt: dev packages are forbidden: "
            + ",".join(unexpected_runtime)
        )
    if tools.get("pip-tools") != "7.5.2":
        errors.append("lock-tools.txt: pip-tools must be exactly 7.5.2")
    for package, version in runtime.items():
        if dev.get(package) != version:
            errors.append(
                f"api-dev.lock.txt: runtime package mismatch {package} "
                f"(runtime={version}, dev={dev.get(package)})"
            )
    return errors


def main() -> int:
    errors = verify_contract()
    if errors:
        print("LOCK_VERIFIER = FAIL")
        for error in errors:
            print(f"ERROR = {error}")
        return 1
    print("LOCK_FILES_EXIST = YES")
    print("ALL_INSTALLABLE_LINES_PINNED = YES")
    print("HASHES_PRESENT = YES")
    print("FASTAPI_EXACTLY_0_116_1 = YES")
    print("UVICORN_EXACTLY_0_51_0 = YES")
    print("RUNTIME_DEV_TOOLING_ABSENT = YES")
    print("NO_ABSOLUTE_PATHS = YES")
    print("NO_CREDENTIALS = YES")
    print("NO_EDITABLE_PROJECT_ENTRY = YES")
    print("NO_UNCONTROLLED_INDEX_URL = YES")
    print("LOCK_VERIFIER = PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
