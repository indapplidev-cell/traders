"""Deterministically regenerate the hash-locked runtime and development contracts."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _header(*, manifest_hash: str, target: str, command: str, generated_date: str) -> str:
    return "\n".join(
        (
            "# Generated dependency contract. Do not edit by hand.",
            "# Source manifest: pyproject.toml",
            f"# Source manifest SHA256: {manifest_hash}",
            f"# Target: {target}",
            "# Generator: pip-tools 7.5.2 (pip-compile)",
            f"# Command: {command}",
            f"# Generated at UTC: {generated_date}",
            "",
        )
    )


def _compile(
    pip_compile: Path,
    output: Path,
    constraint: Path,
    *,
    extra: str | None,
) -> None:
    command = [
        str(pip_compile),
        str(ROOT / "pyproject.toml"),
        "--output-file",
        str(output),
        "--constraint",
        str(constraint),
        "--generate-hashes",
        "--resolver",
        "backtracking",
        "--no-emit-index-url",
        "--no-header",
        "--no-annotate",
        "--strip-extras",
        "--quiet",
    ]
    if extra:
        command.extend(("--extra", extra))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pip-compile", type=Path, required=True)
    parser.add_argument("--generated-date", required=True)
    parser.add_argument("--output-directory", type=Path, default=ROOT / "requirements")
    args = parser.parse_args()

    manifest_hash = hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()
    runtime_lock = ROOT / "requirements" / "api-runtime.lock.txt"
    dev_lock = ROOT / "requirements" / "api-dev.lock.txt"
    args.output_directory.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="traders-lock-", dir=args.output_directory) as tmp:
        tmp_path = Path(tmp)
        runtime_body = tmp_path / "runtime.txt"
        dev_body = tmp_path / "dev.txt"
        _compile(args.pip_compile, runtime_body, runtime_lock, extra=None)
        _compile(args.pip_compile, dev_body, dev_lock, extra="dev")

        common = "pip-compile pyproject.toml --constraint <CURRENT_LOCK> --generate-hashes --resolver backtracking --no-emit-index-url --no-header --no-annotate --strip-extras"
        target = "CPython 3.11; all-platform lock with PEP 508 markers; Linux production evaluation"
        outputs = (
            (
                args.output_directory / "api-runtime.lock.txt",
                _header(
                    manifest_hash=manifest_hash,
                    target=target,
                    command=common,
                    generated_date=args.generated_date,
                )
                + runtime_body.read_text(encoding="utf-8"),
            ),
            (
                args.output_directory / "api-dev.lock.txt",
                _header(
                    manifest_hash=manifest_hash,
                    target=target,
                    command=common + " --extra dev",
                    generated_date=args.generated_date,
                )
                + dev_body.read_text(encoding="utf-8"),
            ),
        )
        for path, text in outputs:
            path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
