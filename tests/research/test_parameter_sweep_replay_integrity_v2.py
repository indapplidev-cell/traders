from __future__ import annotations

import pytest

from traders_ml.parameter_sweep.historical_replay import baseline_parity
from traders_ml.parameter_sweep.replay_integrity import (
    cost_provenance, deterministic_signature, frozen_dataset_hash,
    verify_frozen_manifest,
)


def test_manifest_freezes_cutoff_watermarks_profile_and_baseline():
    rows = [{"candidate_id": "c", "cost_provenance": "BINANCE_SNAPSHOT"}]
    manifest = {"dataset_row_count": 1, "dataset_cutoff_at": "2026-01-01T00:00:00Z", "source_watermarks": {}, "profile": "trade-5m-v2", "trade_config_hash": "base"}
    assert verify_frozen_manifest(manifest, rows) == "PASS"
    with pytest.raises(ValueError, match="ROW_COUNT"):
        verify_frozen_manifest({**manifest, "dataset_row_count": 2}, rows)


def test_cost_provenance_is_complete_and_consistent():
    result = cost_provenance([{"cost_provenance": "BINANCE_SNAPSHOT"}, {"cost_provenance": "BINANCE_SNAPSHOT"}])
    assert result["COST_PROVENANCE_COMPLETE"] is True
    assert result["CONSISTENT_SNAPSHOT"] is True


def test_missing_causal_opportunity_is_explained_not_ignored():
    import datetime
    persisted = [{"position_id": "p", "symbol": "BTCUSDT", "side": "LONG", "opened_at": datetime.datetime.fromtimestamp(1, tz=datetime.timezone.utc), "reason_code": "PAPER_POSITION_CLOSED"}]
    result = baseline_parity({"trades": []}, persisted)
    assert result["BASELINE_UNEXPLAINED_MISMATCHES"] == 0
    assert result["DETAILS"][0]["classification"] == "EXPLAINED_BY_DATA_AVAILABILITY"


def test_deterministic_signature_is_order_and_input_stable():
    kwargs = dict(dataset_hash="d", research_hash="r", baseline_hash="b", seed=7, config_ids=["1", "2"], ranking=["2", "1"])
    assert deterministic_signature(**kwargs) == deterministic_signature(**kwargs)
    assert deterministic_signature(**kwargs) != deterministic_signature(**{**kwargs, "seed": 8})
    assert frozen_dataset_hash([{"a": 1}]) == frozen_dataset_hash([{"a": 1}])

