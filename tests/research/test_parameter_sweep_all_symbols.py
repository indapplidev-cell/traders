from __future__ import annotations

import json
from pathlib import Path

from traders_ml.parameter_sweep.all_symbols import AllSymbolsResearchPipeline
from traders_ml.parameter_sweep.universe import ALL_SYMBOLS_ID


class FakePipeline:
    calls: list[str] = []

    def __init__(self, *, progress=None):
        self.progress = progress

    def run(self, *, symbol, output_root, run_id, resume=False):
        self.calls.append(symbol)
        root = output_root / run_id
        root.mkdir(parents=True, exist_ok=True)
        result = {"final_pipeline_status": "COMPLETED", "stop_reason": None}
        best = {
            "search_evaluated": 3,
            "best_positive_net_pnl": {"config_id": f"{symbol}-p", "symbol": symbol,
                                       "parameters": {"dynamic": 1}, "net_pnl": 5,
                                       "expectancy_R": 1, "profit_factor": 2,
                                       "max_drawdown": 1, "trade_count": 2, "wins": 2, "losses": 0},
            "best_net_pnl_fallback": {"config_id": f"{symbol}-f", "symbol": symbol,
                                       "parameters": {"dynamic": 1}, "net_pnl": 5,
                                       "expectancy_R": 1, "profit_factor": 2,
                                       "max_drawdown": 1, "trade_count": 2, "wins": 2, "losses": 0},
            "best_win_count": {"config_id": f"{symbol}-w", "symbol": symbol,
                                "parameters": {"dynamic": 1}, "net_pnl": -1,
                                "expectancy_R": 1, "profit_factor": 2,
                                "max_drawdown": 1, "trade_count": 4, "wins": 4, "losses": 0},
        }
        (root / "BEST_CONFIGS.json").write_text(json.dumps(best), encoding="utf-8")
        return result


def test_all_resolves_dynamic_universe_and_runs_each_symbol_once(tmp_path, monkeypatch):
    from traders_ml.parameter_sweep import all_symbols
    FakePipeline.calls = []
    monkeypatch.setattr(all_symbols, "resolve_parameter_sweep_universe",
                        lambda: ("trading-universe-v2", ("AAAUSDT", "BBBUSDT")))
    result = AllSymbolsResearchPipeline(
        pipeline_factory=lambda: FakePipeline(),
    ).run(output_root=tmp_path, run_id="all")
    assert FakePipeline.calls == ["AAAUSDT", "BBBUSDT"]
    assert result["mode"] == ALL_SYMBOLS_ID
    assert result["completed_symbols"] == 2
    assert result["best_positive_net_pnl"]["symbol"] in FakePipeline.calls
    assert result["best_win_count"]["symbol"] in FakePipeline.calls
    assert result["cross_symbol_sample_merge"] is False
    assert (tmp_path / "all" / "ALL_SUMMARY.json").is_file()
    assert (tmp_path / "all" / "ALL_BEST_CONFIGS.json").is_file()


def test_all_resume_skips_completed_symbols(tmp_path, monkeypatch):
    from traders_ml.parameter_sweep import all_symbols
    monkeypatch.setattr(all_symbols, "resolve_parameter_sweep_universe",
                        lambda: ("trading-universe-v2", ("AAAUSDT", "BBBUSDT")))
    first = AllSymbolsResearchPipeline(pipeline_factory=lambda: FakePipeline())
    first.run(output_root=tmp_path, run_id="resume")
    FakePipeline.calls = []
    resumed = AllSymbolsResearchPipeline(pipeline_factory=lambda: FakePipeline()).run(
        output_root=tmp_path, run_id="resume", resume=True,
    )
    assert FakePipeline.calls == []
    assert resumed["status"] == "COMPLETED"
