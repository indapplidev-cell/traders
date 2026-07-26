from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "verify_api_dependency_lock.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_api_dependency_lock", VERIFIER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dependency_contract_is_complete_and_hash_locked() -> None:
    verifier = _load_verifier()
    assert verifier.verify_contract() == []


def test_dependency_contract_cli_reports_pass() -> None:
    completed = subprocess.run(
        [sys.executable, str(VERIFIER)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "LOCK_VERIFIER = PASS" in completed.stdout
