from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from app.engine_paper.production_readiness import MIGRATION_MANIFESTS


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "alembic/versions/0013_paper_first_canary_correlation.py"
EXPECTED = "08f9f65acfef946e89dd41297ba14a1dbeb113b62a91a22331a64b5adf620f54"


def test_0013_checkout_bytes_and_manifest_match_accepted_git_blob():
    payload = PATH.read_bytes()
    blob = subprocess.run(
        ["git", "show", "HEAD:alembic/versions/0013_paper_first_canary_correlation.py"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout
    manifest = next(item for item in MIGRATION_MANIFESTS if item.revision.startswith("0013_"))
    canonical_payload = payload.replace(b"\r\n", b"\n")
    assert hashlib.sha256(canonical_payload).hexdigest() == EXPECTED
    assert hashlib.sha256(blob).hexdigest() == EXPECTED == manifest.source_sha256


def test_gitattributes_freezes_only_lf_accepted_0013_revision():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "alembic/versions/0013_paper_first_canary_correlation.py text eol=lf" in attributes
    assert "alembic/versions/*.py text eol=lf" not in attributes
