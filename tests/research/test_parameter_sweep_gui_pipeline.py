from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pytest

from traders_ml.parameter_sweep.pipeline import (
    PHASE_ORDER, PIPELINE_NAME, SingleSymbolResearchPipeline,
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class FakeStages:
    def __init__(
        self, *, ranges: int = 1, limited: bool = False,
        symbol_override: str | None = None, fail_at: str | None = None,
    ) -> None:
        self.ranges = ranges
        self.limited = limited
        self.symbol_override = symbol_override
        self.fail_at = fail_at
        self.calls: list[str] = []
        self.cancel_hook = None

    def separability(self, *, symbol: str, output: Path):
        self.calls.append("SEPARABILITY")
        if self.fail_at == "SEPARABILITY":
            raise ValueError("SEPARABILITY_UNAVAILABLE")
        selected = self.symbol_override or symbol
        dataset = "" if self.limited else json.dumps({"symbol": selected, "profile": "trade-5m-v2"}) + "\n"
        output.mkdir(parents=True, exist_ok=True)
        (output / "SEPARABILITY_DATASET.jsonl").write_text(dataset, encoding="utf-8")
        dataset_hash = sha256(dataset.encode()).hexdigest()
        manifest = {
            "symbol": selected, "profile": "trade-5m-v2",
            "final_status": "PASS_LIMITED_SAMPLE" if self.limited else "PASS",
            "sample_adequacy": "NO_BINARY_OUTCOMES" if self.limited else "USABLE",
            "closed_trades": 0 if self.limited else 3,
            "wins": 0 if self.limited else 2, "losses": 0 if self.limited else 1,
            "dataset_sha256": dataset_hash,
        }
        _write_json(output / "SEPARABILITY_DATASET_MANIFEST.json", manifest)
        _write_json(output / "SEPARABILITY_HANDOFF.json", {"artifact": "SEPARABILITY_HANDOFF"})
        for name in ("FEATURE_REGISTRY.json", "FEATURE_ACTIVITY.json", "INTERACTION_SCREEN.json"):
            _write_json(output / name, [])
        return {"manifest": manifest}

    def range_generation(self, *, input_dir: Path, output: Path):
        self.calls.append("DATA_DRIVEN_RANGE_GENERATION")
        if self.fail_at == "DATA_DRIVEN_RANGE_GENERATION":
            raise ValueError("RANGE_FAILURE")
        manifest = json.loads((input_dir / "SEPARABILITY_DATASET_MANIFEST.json").read_text())
        parameters = [
            {"parameter": f"p{i}", "eligible_for_search": True, "provisional": self.limited}
            for i in range(self.ranges)
        ]
        handoff = {
            "artifact": "DATA_DRIVEN_RANGE_HANDOFF", "symbol": manifest["symbol"],
            "profile": manifest["profile"], "parameters": parameters,
        }
        _write_json(output / "DATA_DRIVEN_RANGE_HANDOFF.json", handoff)
        return {"handoff": handoff}

    def expanded(self, **kwargs):
        self.calls.append("EXPANDED_AUTOMATIC_SEARCH")
        if self.fail_at == "EXPANDED_AUTOMATIC_SEARCH":
            raise ValueError("EXPANDED_FAILURE")
        output, symbol = kwargs["output"], kwargs["symbol"]
        range_hash = _sha(kwargs["handoff_path"])
        handoff = {
            "artifact": "EXPANDED_SEARCH_HANDOFF", "symbol": symbol,
            "profile": "trade-5m-v2", "search_source": "DATA_DRIVEN_RANGE_HANDOFF",
            "range_handoff_fingerprint": range_hash,
        }
        _write_json(output / "EXPANDED_SEARCH_HANDOFF.json", handoff)
        for name, value in (
            ("EXPANDED_SEARCH_CONFIG.json", {}), ("BEHAVIORAL_CLUSTERS.json", {}),
            ("SEARCH_VALUE_NORMALIZATION.json", {}),
        ):
            _write_json(output / name, value)
        (output / "EXPANDED_SEARCH_RESULTS.jsonl").write_text("", encoding="utf-8")
        if self.cancel_hook:
            self.cancel_hook()
        return {
            "handoff": handoff,
            "status": {"PLANNED_CONFIGS": 2, "EVALUATED_CONFIGS": 2, "BEHAVIORALLY_DISTINCT_CONFIGS": 1},
        }

    def adaptive(self, **kwargs):
        self.calls.append("ADAPTIVE_REFINEMENT")
        if self.fail_at == "ADAPTIVE_REFINEMENT":
            raise ValueError("ADAPTIVE_FAILURE")
        handoff = {
            "artifact": "ADAPTIVE_REFINEMENT_HANDOFF", "symbol": kwargs["symbol"],
            "profile": "trade-5m-v2",
            "campaign_inputs": {"expanded_search_fingerprint": "a" * 64},
        }
        _write_json(kwargs["output"] / "ADAPTIVE_REFINEMENT_HANDOFF.json", handoff)
        return {"handoff": handoff, "status": {"ADAPTIVE_ROUNDS": 1, "NEW_BEHAVIORAL_CLUSTERS_DISCOVERED": 1, "STOP_REASON": "NO_NEW_CANDIDATES"}}


def _pipeline(stages: FakeStages) -> SingleSymbolResearchPipeline:
    return SingleSymbolResearchPipeline(
        separability_runner=stages.separability,
        range_runner=stages.range_generation,
        expanded_runner=stages.expanded,
        adaptive_runner=stages.adaptive,
    )


@pytest.mark.parametrize("symbol", ("DOGEUSDT", "LINKUSDT", "SUIUSDT"))
def test_universal_default_route_and_symbol_binding(tmp_path: Path, symbol: str):
    stages = FakeStages()
    result = _pipeline(stages).run(symbol=symbol, output_root=tmp_path, run_id=symbol.lower())
    assert stages.calls == list(PHASE_ORDER[:4])
    assert result["selected_symbol"] == symbol
    assert result["gui_orchestrator"] == PIPELINE_NAME
    assert result["final_pipeline_status"] == "COMPLETED"
    assert result["search_source"] == "DATA_DRIVEN_RANGE_HANDOFF"
    assert result["adaptive_source"] == "EXPANDED_SEARCH_HANDOFF"
    assert result["legacy_targeted_staged_used"] is False
    assert result["legacy_array_fallback"] == 0
    assert result["next_stage_available"] == "VALIDATION_RANKING"


def test_no_evidence_or_ranges_stops_without_legacy(tmp_path: Path):
    stages = FakeStages(ranges=0, limited=True)
    result = _pipeline(stages).run(symbol="DOGEUSDT", output_root=tmp_path, run_id="zero")
    assert stages.calls == ["SEPARABILITY", "DATA_DRIVEN_RANGE_GENERATION"]
    assert result["final_pipeline_status"] == "STOPPED"
    assert result["stop_reason"] == "STOPPED_NO_DATA_DRIVEN_SEARCH_RANGES"
    assert result["legacy_fallback_used"] is False


def test_low_sample_provisional_ranges_continue(tmp_path: Path):
    stages = FakeStages(limited=True)
    result = _pipeline(stages).run(symbol="LINKUSDT", output_root=tmp_path, run_id="limited")
    assert stages.calls == list(PHASE_ORDER[:4])
    assert result["separability_status"] == "LIMITED"
    assert result["phase_summary"]["DATA_DRIVEN_RANGE_GENERATION"]["provisional_count"] == 1


def test_symbol_mismatch_fails_closed(tmp_path: Path):
    stages = FakeStages(symbol_override="LINKUSDT")
    result = _pipeline(stages).run(symbol="DOGEUSDT", output_root=tmp_path, run_id="mismatch")
    assert result["final_pipeline_status"] == "FAILED"
    assert result["stop_reason"] == "FAIL_CLOSED_SYMBOL_MISMATCH"
    assert stages.calls == ["SEPARABILITY"]


def test_phase_failure_prevents_downstream(tmp_path: Path):
    stages = FakeStages(fail_at="EXPANDED_AUTOMATIC_SEARCH")
    result = _pipeline(stages).run(symbol="SUIUSDT", output_root=tmp_path, run_id="failed")
    assert result["final_pipeline_status"] == "FAILED"
    assert "ADAPTIVE_REFINEMENT" not in stages.calls


def test_cancel_during_expanded_prevents_adaptive(tmp_path: Path):
    stages = FakeStages()
    pipeline = _pipeline(stages)
    stages.cancel_hook = pipeline.request_cancel
    result = pipeline.run(symbol="DOGEUSDT", output_root=tmp_path, run_id="cancel")
    assert result["final_pipeline_status"] == "CANCELLED"
    assert stages.calls == list(PHASE_ORDER[:3])


def test_resume_same_chain_succeeds_and_tamper_fails_closed(tmp_path: Path):
    stages = FakeStages()
    pipeline = _pipeline(stages)
    stages.cancel_hook = pipeline.request_cancel
    pipeline.run(symbol="DOGEUSDT", output_root=tmp_path, run_id="resume")
    stages.cancel_hook = None
    resumed = pipeline.run(symbol="DOGEUSDT", output_root=tmp_path, run_id="resume", resume=True)
    assert resumed["final_pipeline_status"] == "COMPLETED"
    with pytest.raises(ValueError, match="FAIL_CLOSED_SYMBOL_MISMATCH"):
        pipeline.run(symbol="LINKUSDT", output_root=tmp_path, run_id="resume", resume=True)
    handoff = tmp_path / "resume" / "02_data_driven_ranges" / "DATA_DRIVEN_RANGE_HANDOFF.json"
    handoff.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="FAIL_CLOSED_HANDOFF_MISMATCH"):
        pipeline.run(symbol="DOGEUSDT", output_root=tmp_path, run_id="resume", resume=True)


def test_manifest_chain_and_production_safety(tmp_path: Path):
    stages = FakeStages()
    result = _pipeline(stages).run(symbol="DOGEUSDT", output_root=tmp_path, run_id="safe")
    assert all(result[field] for field in (
        "separability_handoff_fingerprint", "range_handoff_fingerprint",
        "expanded_search_handoff_fingerprint", "adaptive_handoff_fingerprint",
    ))
    assert result["validation_ranking_executed"] is False
    assert result["finalist_freeze_executed"] is False
    assert result["holdout_opened"] is False
    assert result["live_state"] is False
    assert result["binance_order_calls"] == result["production_mutations"] == 0


def test_no_runtime_symbol_hardcode_default_or_branch():
    root = Path(__file__).resolve().parents[2]
    source = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "traders_ml/parameter_sweep/pipeline.py",
            "traders_ml/parameter_sweep/controller.py",
            "traders_ml/parameter_sweep/ui.py",
        )
    )
    assert 'symbol = "DOGEUSDT"' not in source
    assert 'or "DOGEUSDT"' not in source
    assert 'if symbol == "DOGEUSDT"' not in source


def test_gui_all_is_the_only_implicit_ui_mode():
    root = Path(__file__).resolve().parents[2]
    source = (root / "traders_ml/parameter_sweep/ui.py").read_text(encoding="utf-8")
    assert "values=(ResearchMode.ALL.value,)" in source
