from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.market_data_image_contract import (
    ApprovedScanTarget,
    classify_scan_path,
    deduplicate_findings,
    discover_tracked_targets,
    scan_allowed_file,
    scan_tree,
)
from scripts.verify_persistent_secret_binding import CANONICAL_BINDING, ROOT


SYNTHETIC_SECRET = "synthetic-value-that-must-never-be-rendered"


def _protected(decision) -> None:
    assert decision.decision == "EXCLUDED_BEFORE_READ"
    assert decision.category == "PROTECTED_BINDING"


def test_exact_and_relative_protected_binding_are_excluded_before_read() -> None:
    _protected(classify_scan_path(CANONICAL_BINDING, ROOT))
    _protected(classify_scan_path(".env.production.local", ROOT))


@pytest.mark.parametrize(
    "variant",
        (
            ".ENV.PRODUCTION.LOCAL",
            r".\.Env.PRODUCTION.Local",
        "./.env.production.local",
        r"nested\..\ .env.production.local".replace(r"\ ", "\\"),
        ".env.service.local",
        "runtime.secret",
        "runtime.secrets",
    ),
)
def test_case_slash_traversal_and_protected_pattern_variants_are_denied(
    variant: str,
) -> None:
    _protected(classify_scan_path(variant, ROOT))


def test_explicit_allowlist_cannot_override_protected_binding_deny() -> None:
    approved, excluded = discover_tracked_targets(
        ROOT,
        explicit_safe_paths=[CANONICAL_BINDING],
        inventory=lambda _root: b"",
    )
    assert approved == []
    assert excluded == [
        {
            "rule_id": "PROTECTED_BINDING",
            "path": ".env.production.local",
            "line": 0,
            "category": "PROTECTED_BINDING",
            "severity": "INFO",
            "count": 1,
            "decision": "EXCLUDED_BEFORE_READ",
        }
    ]


def test_discovery_uses_only_git_inventory_and_excludes_unlisted_files() -> None:
    calls: list[Path] = []

    def inventory(root: Path) -> bytes:
        calls.append(root)
        return b"app/safe.py\0"

    approved, excluded = discover_tracked_targets(ROOT, inventory=inventory)

    assert calls == [ROOT]
    assert excluded == []
    assert [item.normalized_path for item in approved] == ["app/safe.py"]
    assert all("untracked" not in item.normalized_path for item in approved)
    assert all("ignored" not in item.normalized_path for item in approved)


def test_resolved_link_indirection_into_protected_binding_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_resolve = Path.resolve

    def resolve(path: Path, strict: bool = False) -> Path:
        if path.name == "safe-link.py":
            return CANONICAL_BINDING
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", resolve)

    _protected(classify_scan_path("safe-link.py", ROOT))


def test_repository_prefix_confusion_and_outside_traversal_are_denied() -> None:
    sibling = ROOT.parent / f"{ROOT.name}-other" / "safe.py"
    decision = classify_scan_path(sibling, ROOT)
    assert decision.decision == "EXCLUDED_BEFORE_READ"
    assert decision.category == "OUTSIDE_REPOSITORY"


def test_synthetic_secret_finding_contains_safe_metadata_only() -> None:
    data = (
        b'password' + b'="' + SYNTHETIC_SECRET.encode("ascii") + b'"\n'
    )
    target = ApprovedScanTarget(ROOT / "app" / "safe.py", "app/safe.py")

    findings = scan_allowed_file(target, reader=lambda _path: data)

    assert findings == [
        {
            "rule_id": "SECRET_ASSIGNMENT",
            "path": "app/safe.py",
            "line": 1,
            "category": "SECRET_MATERIAL",
            "severity": "HIGH",
            "count": 1,
        }
    ]


def test_serialized_output_excludes_secret_and_deterministic_derived_forms() -> None:
    data = (
        b'password' + b'="' + SYNTHETIC_SECRET.encode("ascii") + b'"\n'
    )
    target = ApprovedScanTarget(ROOT / "app" / "safe.py", "app/safe.py")
    rendered = json.dumps(scan_allowed_file(target, reader=lambda _path: data))
    derived = {
        SYNTHETIC_SECRET,
        SYNTHETIC_SECRET[:8],
        SYNTHETIC_SECRET[-8:],
        SYNTHETIC_SECRET.encode("ascii").hex(),
        base64.b64encode(SYNTHETIC_SECRET.encode("ascii")).decode("ascii"),
        hashlib.sha256(SYNTHETIC_SECRET.encode("ascii")).hexdigest(),
    }
    assert all(value not in rendered for value in derived)
    assert "fingerprint" not in rendered.casefold()
    assert "hash" not in rendered.casefold()


def test_deduplication_uses_rule_normalized_path_and_line() -> None:
    first = {
        "rule_id": "SECRET_ASSIGNMENT",
        "path": r"app\safe.py",
        "line": 7,
        "category": "SECRET_MATERIAL",
        "severity": "HIGH",
        "count": 1,
    }
    second = {**first, "path": "APP/safe.py"}

    assert deduplicate_findings([first, second]) == [{**first, "count": 2}]


def test_normal_tracked_source_is_approved_and_scanned() -> None:
    approved, excluded = discover_tracked_targets(
        ROOT,
        inventory=lambda _root: b"app/safe.py\0",
    )
    assert excluded == []
    assert len(approved) == 1
    assert scan_allowed_file(approved[0], reader=lambda _path: b"ordinary = 1\n") == []


def test_discovery_never_recursively_walks_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("recursive repository walk is forbidden")

    monkeypatch.setattr(Path, "rglob", forbidden)
    monkeypatch.setattr(os, "walk", forbidden)

    assert scan_tree(ROOT, inventory=lambda _root: b"") == []


def test_unreadable_allowed_file_reports_safe_error_metadata() -> None:
    target = ApprovedScanTarget(ROOT / "app" / "safe.py", "app/safe.py")

    finding = scan_allowed_file(
        target,
        reader=lambda _path: (_ for _ in ()).throw(PermissionError()),
    )

    assert finding == [
        {
            "rule_id": "UNREADABLE_FILE",
            "path": "app/safe.py",
            "line": 0,
            "category": "SCAN_ERROR",
            "severity": "ERROR",
            "count": 1,
        }
    ]


def test_real_binding_metadata_only_verification_never_opens_or_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counters = {"open": 0, "read": 0}

    def forbidden_open(*_args, **_kwargs):
        counters["open"] += 1
        raise AssertionError("protected binding open attempted")

    def forbidden_read(*_args, **_kwargs):
        counters["read"] += 1
        raise AssertionError("protected binding read attempted")

    monkeypatch.setattr(Path, "open", forbidden_open)
    monkeypatch.setattr(Path, "read_text", forbidden_read)
    monkeypatch.setattr(Path, "read_bytes", forbidden_read)

    assert os.path.exists(CANONICAL_BINDING)
    ignored = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", "--", ".env.production.local"],
        check=False,
    )
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "--error-unmatch",
            "--",
            ".env.production.local",
        ],
        check=False,
        capture_output=True,
    )
    findings = scan_tree(
        ROOT,
        explicit_safe_paths=[CANONICAL_BINDING],
        inventory=lambda _root: b"",
    )

    assert ignored.returncode == 0
    assert tracked.returncode != 0
    assert counters == {"open": 0, "read": 0}
    assert findings[0]["decision"] == "EXCLUDED_BEFORE_READ"
