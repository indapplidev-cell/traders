"""No-echo CLI for tracked Compose key and policy inspection."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_retry_controls import (
    PROTECTED_BINDING_NAME,
    inspect_tracked_compose_key,
    render_safe_items,
    tracked_compose_policy,
)


def _is_tracked(path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return False
    return (
        subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", relative],
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--key-path")
    parser.add_argument("--policy", action="store_true")
    args = parser.parse_args(argv)
    path = args.file
    if path.name.casefold() == PROTECTED_BINDING_NAME.casefold():
        print(f"file={path.name}")
        print("policy_result=FAIL")
        print("error_class=PROTECTED_BINDING_EXCLUDED_BEFORE_READ")
        return 2
    if not _is_tracked(path):
        print(f"file={path.name}")
        print("policy_result=FAIL")
        print("error_class=FILE_NOT_TRACKED")
        return 2
    if args.policy:
        findings = tracked_compose_policy(path)
        print(render_safe_items(findings))
        return int(
            any(
                getattr(getattr(item, "policy_result", None), "value", "FAIL")
                == "FAIL"
                for item in findings
            )
        )
    if not args.key_path:
        print(f"file={path.name}")
        print("policy_result=FAIL")
        print("error_class=KEY_PATH_REQUIRED")
        return 2
    inspection = inspect_tracked_compose_key(path, args.key_path)
    print(inspection.render())
    return int(inspection.policy_result.value != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
