from __future__ import annotations

import json
from pathlib import Path

from scripts.market_data_image_contract import (
    compare_inventory,
    linux_effective_lock,
    parse_lock,
)


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements" / "api-runtime.lock.txt"


def test_linux_effective_lock_applies_platform_markers() -> None:
    all_platform = parse_lock(LOCK)
    linux = linux_effective_lock(all_platform)
    assert len(all_platform) == 24
    assert len(linux) == 22
    assert "colorama" not in linux
    assert "tzdata" not in linux


def test_linux_inventory_comparison_is_exact_and_ignores_base_bootstrap_tools() -> None:
    expected = linux_effective_lock(parse_lock(LOCK))
    actual = dict(expected)
    actual.update(
        {
            "packaging": "base-image-contract",
            "pip": "base-image-contract",
            "setuptools": "base-image-contract",
            "traders-ml": "0.2.0",
            "wheel": "base-image-contract",
        }
    )
    comparison = compare_inventory(expected, actual)
    assert comparison["missing"] == []
    assert comparison["version_mismatches"] == []
    assert comparison["unexpected"] == []
    json.dumps(comparison)


def test_linux_inventory_comparison_rejects_drift() -> None:
    expected = linux_effective_lock(parse_lock(LOCK))
    actual = dict(expected)
    actual.pop("fastapi")
    actual["uvicorn"] = "0"
    actual["unknown-runtime"] = "1"
    comparison = compare_inventory(expected, actual)
    assert comparison["missing"] == ["fastapi"]
    assert comparison["version_mismatches"] == ["uvicorn"]
    assert comparison["unexpected"] == ["unknown-runtime"]
