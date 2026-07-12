from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = REPOSITORY_ROOT / "reports" / "engine_trend" / "acceptance_pack"
MANIFEST_PATH = PACK_ROOT / "ENGINE_TREND_13_ARTIFACT_MANIFEST.json"
EXPECTED_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}


def load_manifest() -> dict[str, object]:
    assert MANIFEST_PATH.is_file()
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_manifest_contract_and_supported_inputs() -> None:
    manifest = load_manifest()
    assert manifest["stage"] == "ENGINE-TREND-13"
    supported = manifest["supported_inputs"]
    assert set(supported["symbols"]) == EXPECTED_SYMBOLS
    assert supported["intervals"] == ["15m"]


def test_acceptance_results_preserve_output_and_safety_contract() -> None:
    results = load_manifest()["acceptance_results"]
    assert len(results) == 3
    assert {result["symbol"] for result in results} == EXPECTED_SYMBOLS
    for result in results:
        assert result["interval"] == "15m"
        assert result["candles_loaded"] == 96
        assert result["boundary_status"] == "READY"
        assert result["market_regime"] in {"UP", "DOWN", "FLAT", "UNKNOWN"}
        assert result["trade_signal"] == "NOT_EVALUATED"
        assert result["safe_for_runtime_trading"] is False
        assert result["live_trading_connected"] is False


def test_artifact_paths_and_sha256_match_committed_evidence() -> None:
    for result in load_manifest()["acceptance_results"]:
        for artifact_key, checksum_key in (
            ("preview_artifact", "sha256_preview"),
            ("result_artifact", "sha256_result"),
        ):
            artifact = REPOSITORY_ROOT / result[artifact_key]
            assert artifact.is_file(), f"missing acceptance evidence: {artifact}"
            assert sha256(artifact) == result[checksum_key]


def test_manifest_contains_no_unmasked_database_url_or_password_value() -> None:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    assert not re.search(r"postgresql(?:\+psycopg2?)?://", text, re.IGNORECASE)
    assert not re.search(r'"(?:password|db_url|database_url)"\s*:', text, re.IGNORECASE)


def test_acceptance_documents_exist() -> None:
    for filename in (
        "ENGINE_TREND_13_ACCEPTANCE_PACK.md",
        "ENGINE_TREND_13_COMMANDS.md",
        "ENGINE_TREND_13_SAFETY_CHECKLIST.md",
    ):
        assert (PACK_ROOT / filename).is_file()
