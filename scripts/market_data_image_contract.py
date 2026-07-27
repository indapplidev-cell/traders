"""Marker-aware dependency and redacted image-content security gates."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_DISTRIBUTIONS = frozenset(
    {"packaging", "pip", "setuptools", "traders-ml", "wheel"}
)
EXPECTED_MARKERS = {
    "colorama": 'platform_system == "Windows"',
    "tzdata": 'sys_platform == "win32"',
}
URI_RULE = re.compile(
    rb"(?i)\b[a-z][a-z0-9+.-]*" + b":" + b"//" + rb"[^\s/'\"<>:@]+:[^\s/'\"<>@]+@"
)
PRIVATE_KEY_RULE = re.compile(
    b"-" * 5 + rb"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY" + b"-" * 5
)
SECRET_ASSIGNMENT_RULE = re.compile(
    rb"(?i)\b(?:passw" + b"ord|api[_-]?key|access[_-]?token|secret)[A-Za-z0-9_-]*"
    rb"\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"
)
RULES = (
    ("CREDENTIAL_BEARING_URI", URI_RULE),
    ("PRIVATE_KEY", PRIVATE_KEY_RULE),
    ("SECRET_ASSIGNMENT", SECRET_ASSIGNMENT_RULE),
)


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class LockedDistribution:
    name: str
    version: str
    marker: str | None


def logical_lock_lines(text: str) -> list[str]:
    logical: list[str] = []
    current = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            current += stripped[:-1].rstrip() + " "
            continue
        logical.append(current + stripped)
        current = ""
    if current:
        logical.append(current)
    return logical


def parse_lock(path: Path) -> dict[str, LockedDistribution]:
    result: dict[str, LockedDistribution] = {}
    pattern = re.compile(
        r"^(?P<name>[A-Za-z0-9._-]+)(?:\[[^]]+\])?==(?P<version>[^\s;]+)"
        r"(?:\s*;\s*(?P<marker>.+?))?\s*(?:--hash=|$)"
    )
    for line in logical_lock_lines(path.read_text(encoding="utf-8")):
        match = pattern.match(line)
        if match is None:
            raise ValueError(f"unparseable locked requirement in {path.name}")
        name = canonical_name(match.group("name"))
        marker = match.group("marker")
        result[name] = LockedDistribution(name, match.group("version"), marker)
    return result


def linux_effective_lock(
    locked: dict[str, LockedDistribution],
) -> dict[str, str]:
    effective: dict[str, str] = {}
    for name, distribution in locked.items():
        if distribution.marker is None:
            effective[name] = distribution.version
            continue
        if EXPECTED_MARKERS.get(name) != distribution.marker:
            raise ValueError(f"unsupported marker for {name}")
    return effective


def compare_inventory(
    expected: dict[str, str], actual: dict[str, str]
) -> dict[str, object]:
    normalized_actual = {canonical_name(k): v for k, v in actual.items()}
    runtime_actual = {
        k: v for k, v in normalized_actual.items() if k not in BOOTSTRAP_DISTRIBUTIONS
    }
    missing = sorted(k for k in expected if k not in runtime_actual)
    mismatches = sorted(
        k for k in expected if k in runtime_actual and expected[k] != runtime_actual[k]
    )
    unexpected = sorted(k for k in runtime_actual if k not in expected)
    return {
        "expected_count": len(expected),
        "actual_runtime_count": len(runtime_actual),
        "missing": missing,
        "version_mismatches": mismatches,
        "unexpected": unexpected,
        "bootstrap_distributions": sorted(
            k for k in normalized_actual if k in BOOTSTRAP_DISTRIBUTIONS
        ),
    }


def _scan_blob(data: bytes, location: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for rule_id, pattern in RULES:
        for match in pattern.finditer(data):
            fingerprint = hashlib.sha256(match.group(0)).hexdigest()[:16]
            findings.append(
                {
                    "location": location,
                    "rule_id": rule_id,
                    "redacted_fingerprint": fingerprint,
                }
            )
    return findings


def scan_paths(paths: Iterable[Path], base: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(base).as_posix()
        if any(part in {".git", ".mypy_cache", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            findings.append(
                {
                    "location": relative,
                    "rule_id": "CREDENTIAL_FILE",
                    "redacted_fingerprint": hashlib.sha256(relative.encode()).hexdigest()[:16],
                }
            )
        try:
            data = path.read_bytes()
            findings.extend(_scan_blob(data, relative))
            if path.suffix.lower() in {".whl", ".zip"}:
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        for name in archive.namelist():
                            if not name.endswith("/"):
                                findings.extend(
                                    _scan_blob(
                                        archive.read(name),
                                        f"{relative}:{name}",
                                    )
                                )
                except zipfile.BadZipFile:
                    pass
        except OSError:
            findings.append(
                {
                    "location": relative,
                    "rule_id": "UNREADABLE_FILE",
                    "redacted_fingerprint": hashlib.sha256(relative.encode()).hexdigest()[:16],
                }
            )
    return findings


def scan_tree(root: Path) -> list[dict[str, str]]:
    return scan_paths(root.rglob("*"), root)


def scan_docker_save(path: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    with tarfile.open(path, "r:*") as outer:
        for member in outer.getmembers():
            if not member.isfile():
                continue
            extracted = outer.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            location = f"docker-save:{member.name}"
            findings.extend(_scan_blob(data, location))
            if member.name.endswith(".tar"):
                try:
                    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as layer:
                        for inner in layer.getmembers():
                            if not inner.isfile():
                                continue
                            inner_file = layer.extractfile(inner)
                            if inner_file is not None:
                                findings.extend(
                                    _scan_blob(
                                        inner_file.read(),
                                        f"{location}:{inner.name}",
                                    )
                                )
                except tarfile.TarError:
                    pass
    return findings


def _emit_findings(findings: list[dict[str, str]]) -> int:
    print(json.dumps({"count": len(findings), "findings": findings}, sort_keys=True))
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    source_parser = subparsers.add_parser("scan-tree")
    source_parser.add_argument("root", type=Path)
    image_parser = subparsers.add_parser("scan-docker-save")
    image_parser.add_argument("archive", type=Path)
    compare_parser = subparsers.add_parser("compare-inventory")
    compare_parser.add_argument("--lock", type=Path, required=True)
    compare_parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "scan-tree":
        return _emit_findings(scan_tree(args.root.resolve()))
    if args.command == "scan-docker-save":
        return _emit_findings(scan_docker_save(args.archive.resolve()))
    if args.command == "compare-inventory":
        locked = parse_lock(args.lock)
        expected = linux_effective_lock(locked)
        actual = json.loads(args.inventory.read_text(encoding="utf-8"))
        result = compare_inventory(expected, actual)
        print(json.dumps(result, sort_keys=True))
        return int(
            bool(
                result["missing"]
                or result["version_mismatches"]
                or result["unexpected"]
            )
        )
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
