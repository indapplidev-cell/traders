"""Marker-aware dependency and redacted image-content security gates."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence


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
PROTECTED_BINDING_NAMES = frozenset({".env.production.local", ".env.local"})
PROTECTED_BINDING_SUFFIXES = (".secret", ".secrets")
FORBIDDEN_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "artifacts",
        "credentials",
        "env",
        "evidence_inbox",
        "logs",
        "pgdata",
        "private",
        "reports",
        "secrets",
        "venv",
        ".virtualenv",
    }
)
FORBIDDEN_ARCHIVE_SUFFIXES = frozenset(
    {".7z", ".backup", ".dump", ".gz", ".rar", ".tar", ".tgz", ".whl", ".zip"}
)


@dataclass(frozen=True)
class ScanPathDecision:
    decision: str
    category: str
    normalized_path: str | None = None
    resolved_path: Path | None = None


@dataclass(frozen=True)
class ApprovedScanTarget:
    path: Path
    normalized_path: str


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


def _safe_path_text(path: str | os.PathLike[str]) -> str:
    return os.fspath(path).replace("\\", "/")


def _path_parts(path: str | os.PathLike[str]) -> tuple[str, ...]:
    return tuple(part.casefold() for part in _safe_path_text(path).split("/") if part)


def is_protected_binding(path: str | os.PathLike[str]) -> bool:
    for part in _path_parts(path):
        if part in PROTECTED_BINDING_NAMES:
            return True
        if part.startswith(".env.") and part.endswith(".local"):
            return True
        if part.endswith(PROTECTED_BINDING_SUFFIXES):
            return True
    return False


def _is_forbidden_path(path: str | os.PathLike[str]) -> bool:
    parts = _path_parts(path)
    if is_protected_binding(path):
        return True
    if any(part in FORBIDDEN_DIRECTORY_NAMES for part in parts):
        return True
    return bool(parts and Path(parts[-1]).suffix.casefold() in FORBIDDEN_ARCHIVE_SUFFIXES)


def _is_within(path: Path, root: Path) -> bool:
    try:
        os.path.commonpath((os.path.normcase(str(path)), os.path.normcase(str(root))))
    except ValueError:
        return False
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _safe_report_path(path: str | os.PathLike[str], repository: Path) -> str:
    root = repository.resolve(strict=False)
    candidate = Path(path)
    lexical = candidate if candidate.is_absolute() else root / candidate
    normalized = Path(os.path.abspath(os.path.normpath(str(lexical))))
    if _is_within(normalized, root):
        return normalized.relative_to(root).as_posix()
    return Path(_safe_path_text(path)).name


def classify_scan_path(path: str | os.PathLike[str], repository: Path) -> ScanPathDecision:
    original = _safe_path_text(path)
    if is_protected_binding(original):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "PROTECTED_BINDING")
    if _is_forbidden_path(original):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "FORBIDDEN_PATH")

    root = repository.resolve(strict=False)
    candidate = Path(path)
    lexical = candidate if candidate.is_absolute() else root / candidate
    normalized = Path(os.path.abspath(os.path.normpath(str(lexical))))
    if not _is_within(normalized, root):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "OUTSIDE_REPOSITORY")
    if is_protected_binding(normalized):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "PROTECTED_BINDING")
    if _is_forbidden_path(normalized):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "FORBIDDEN_PATH")

    resolved = normalized.resolve(strict=False)
    if not _is_within(resolved, root):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "OUTSIDE_REPOSITORY")
    if is_protected_binding(resolved):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "PROTECTED_BINDING")
    if _is_forbidden_path(resolved):
        return ScanPathDecision("EXCLUDED_BEFORE_READ", "FORBIDDEN_PATH")

    relative = normalized.relative_to(root).as_posix()
    return ScanPathDecision("ALLOWED", "TRACKED_SOURCE", relative, resolved)


def _git_ls_files(repository: Path) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), "ls-files", "-z"],
        check=True,
        capture_output=True,
    ).stdout


def discover_tracked_targets(
    repository: Path,
    *,
    explicit_safe_paths: Iterable[str | os.PathLike[str]] = (),
    inventory: Callable[[Path], bytes] = _git_ls_files,
) -> tuple[list[ApprovedScanTarget], list[dict[str, object]]]:
    raw = inventory(repository)
    tracked = [item.decode("utf-8") for item in raw.split(b"\0") if item]
    candidates: list[str | os.PathLike[str]] = [*tracked, *explicit_safe_paths]
    approved: list[ApprovedScanTarget] = []
    excluded: list[dict[str, object]] = []
    seen: set[str] = set()
    for candidate in candidates:
        decision = classify_scan_path(candidate, repository)
        if decision.decision != "ALLOWED":
            if decision.category == "PROTECTED_BINDING":
                excluded.append(
                    format_safe_finding(
                        rule_id="PROTECTED_BINDING",
                        path=_safe_report_path(candidate, repository),
                        line=0,
                        category="PROTECTED_BINDING",
                        severity="INFO",
                        decision="EXCLUDED_BEFORE_READ",
                    )
                )
            continue
        assert decision.normalized_path is not None
        assert decision.resolved_path is not None
        key = decision.normalized_path.casefold()
        if key not in seen:
            seen.add(key)
            approved.append(
                ApprovedScanTarget(decision.resolved_path, decision.normalized_path)
            )
    return approved, excluded


def format_safe_finding(
    *,
    rule_id: str,
    path: str,
    line: int,
    category: str,
    severity: str,
    count: int = 1,
    decision: str | None = None,
) -> dict[str, object]:
    finding: dict[str, object] = {
        "rule_id": rule_id,
        "path": path,
        "line": line,
        "category": category,
        "severity": severity,
        "count": count,
    }
    if decision is not None:
        finding["decision"] = decision
    return finding


def _scan_blob(data: bytes, location: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for rule_id, pattern in RULES:
        for match in pattern.finditer(data):
            findings.append(
                format_safe_finding(
                    rule_id=rule_id,
                    path=location,
                    line=data.count(b"\n", 0, match.start()) + 1,
                    category="SECRET_MATERIAL",
                    severity="HIGH",
                )
            )
    return findings


def scan_allowed_file(
    target: ApprovedScanTarget,
    *,
    reader: Callable[[Path], bytes] = Path.read_bytes,
) -> list[dict[str, object]]:
    try:
        return _scan_blob(reader(target.path), target.normalized_path)
    except (OSError, UnicodeError):
        return [
            format_safe_finding(
                rule_id="UNREADABLE_FILE",
                path=target.normalized_path,
                line=0,
                category="SCAN_ERROR",
                severity="ERROR",
            )
        ]


def deduplicate_findings(
    findings: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    deduplicated: dict[tuple[str, str, int], dict[str, object]] = {}
    for finding in findings:
        key = (
            str(finding["rule_id"]),
            str(finding["path"]).replace("\\", "/").casefold(),
            int(finding["line"]),
        )
        if key in deduplicated:
            deduplicated[key]["count"] = int(deduplicated[key]["count"]) + int(
                finding.get("count", 1)
            )
        else:
            deduplicated[key] = dict(finding)
    return list(deduplicated.values())


def scan_paths(
    paths: Iterable[ApprovedScanTarget],
    _base: Path | None = None,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for target in paths:
        if not isinstance(target, ApprovedScanTarget):
            raise TypeError("scan_paths accepts approved targets only")
        findings.extend(scan_allowed_file(target))
    return deduplicate_findings(findings)


def scan_tree(
    root: Path,
    *,
    explicit_safe_paths: Iterable[str | os.PathLike[str]] = (),
    inventory: Callable[[Path], bytes] = _git_ls_files,
) -> list[dict[str, object]]:
    approved, excluded = discover_tracked_targets(
        root,
        explicit_safe_paths=explicit_safe_paths,
        inventory=inventory,
    )
    return deduplicate_findings([*excluded, *scan_paths(approved)])


def scan_docker_save(path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
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
    return deduplicate_findings(findings)


def _emit_findings(findings: list[dict[str, object]]) -> int:
    print(json.dumps({"count": len(findings), "findings": findings}, sort_keys=True))
    return 1 if findings else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    source_parser = subparsers.add_parser("scan-tree")
    source_parser.add_argument("root", type=Path)
    source_parser.add_argument("--safe-path", action="append", default=[])
    image_parser = subparsers.add_parser("scan-docker-save")
    image_parser.add_argument("archive", type=Path)
    compare_parser = subparsers.add_parser("compare-inventory")
    compare_parser.add_argument("--lock", type=Path, required=True)
    compare_parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "scan-tree":
        return _emit_findings(
            scan_tree(
                args.root.resolve(),
                explicit_safe_paths=args.safe_path,
            )
        )
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
