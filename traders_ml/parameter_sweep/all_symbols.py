"""Thin ALL-symbols coordinator for the existing single-symbol pipeline.

This module deliberately owns no search, replay, validation, or ranking rules.
It resolves the production universe at launch, runs one ordinary pipeline per
symbol, and retains only bounded incumbent state plus compact summaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .pipeline import PROFILE, SingleSymbolResearchPipeline
from .universe import ALL_SYMBOLS_ID, resolve_parameter_sweep_universe
from .winners import WinnerTracker


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AllSymbolsResearchPipeline:
    """Run the canonical pipeline once for each dynamically resolved symbol."""

    def __init__(self, *, progress=None, pipeline_factory=None) -> None:
        self._progress = progress or (lambda _value: None)
        self._pipeline_factory = pipeline_factory or (lambda: SingleSymbolResearchPipeline(progress=self._progress))
        self._cancel = False
        self._active_pipeline = None

    def request_cancel(self) -> None:
        self._cancel = True
        if self._active_pipeline is not None:
            self._active_pipeline.request_cancel()

    def _write(self, root: Path, name: str, value: Mapping[str, Any]) -> None:
        DEFAULT_ARTIFACT_WRITER.atomic_json(root / name, dict(value), operation="all_symbols_artifact")

    @staticmethod
    def _summary(symbol: str, result: Mapping[str, Any], best: Mapping[str, Any] | None) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "evaluated": int((best or {}).get("search_evaluated", 0)),
            "positive_leader": (best or {}).get("best_positive_net_pnl"),
            "max_wins": (best or {}).get("best_win_count"),
            "status": result.get("final_pipeline_status", "UNKNOWN"),
            "reason": result.get("stop_reason"),
        }

    def run(self, *, output_root: Path, run_id: str, resume: bool = False) -> dict[str, Any]:
        universe_id, symbols = resolve_parameter_sweep_universe()
        root = output_root / run_id
        root.mkdir(parents=True, exist_ok=True)
        checkpoint_path = root / "ALL_CHECKPOINT.json"
        prior = {}
        if resume and checkpoint_path.is_file():
            prior = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        completed = dict(prior.get("per_symbol", {}))
        failed: dict[str, str] = dict(prior.get("failed_symbols", {}))
        tracker = WinnerTracker.restore(prior.get("global_winners"))
        total_evaluated = int(prior.get("total_evaluated_configs", tracker.evaluated))
        started = prior.get("started_at") or _now()
        self._progress({"artifact": "ALL_SYMBOLS_PROGRESS", "selected_symbol": ALL_SYMBOLS_ID,
                        "resolved_symbols": list(symbols), "completed_symbols": len(completed),
                        "failed_symbols": len(failed), "current_symbol": None,
                        "total_evaluated_configs": total_evaluated})
        for index, symbol in enumerate(symbols, 1):
            if symbol in completed or symbol in failed:
                continue
            if self._cancel:
                break
            self._progress({"artifact": "ALL_SYMBOLS_PROGRESS", "selected_symbol": ALL_SYMBOLS_ID,
                            "resolved_symbols": list(symbols), "completed_symbols": len(completed),
                            "failed_symbols": len(failed), "current_symbol": symbol,
                            "current_symbol_index": index, "current_symbol_count": len(symbols),
                            "total_evaluated_configs": total_evaluated})
            symbol_root = root / "symbols" / symbol
            try:
                pipeline = self._pipeline_factory()
                self._active_pipeline = pipeline
                self._write(root, "ALL_CHECKPOINT.json", {
                    "mode": ALL_SYMBOLS_ID, "universe_id": universe_id, "symbols": list(symbols),
                    "started_at": started, "current_symbol": symbol,
                    "in_progress_symbol": symbol, "completed_symbols": list(completed),
                    "failed_symbols": failed, "per_symbol": completed,
                    "global_winners": tracker.state(), "total_evaluated_configs": total_evaluated,
                })
                result = pipeline.run(
                    symbol=symbol, output_root=root / "symbols", run_id=symbol,
                    resume=bool(resume and symbol == prior.get("in_progress_symbol") and symbol_root.is_dir()),
                )
                best_path = symbol_root / "BEST_CONFIGS.json"
                best = json.loads(best_path.read_text(encoding="utf-8")) if best_path.is_file() else {}
                if result.get("final_pipeline_status") == "CANCELLED":
                    prior["in_progress_symbol"] = symbol
                    break
                completed[symbol] = self._summary(symbol, result, best)
                total_evaluated += int(best.get("search_evaluated", 0))
                for candidate in (best.get("best_positive_net_pnl"), best.get("best_net_pnl_fallback"), best.get("best_win_count")):
                    if candidate:
                        tracker.update({**candidate, "symbol": symbol})
                tracker.evaluated = total_evaluated
            except BaseException as error:
                failed[symbol] = str(getattr(error, "reason", error))
            finally:
                self._active_pipeline = None
            self._write(root, "ALL_CHECKPOINT.json", {
                "mode": ALL_SYMBOLS_ID, "universe_id": universe_id, "symbols": list(symbols),
                "started_at": started, "current_symbol": symbol,
                "completed_symbols": list(completed), "failed_symbols": failed,
                "per_symbol": completed, "global_winners": tracker.state(),
                "total_evaluated_configs": total_evaluated,
            })
        if self._cancel:
            status = "CANCELLED"
        elif failed and completed:
            status = "COMPLETED_WITH_SYMBOL_FAILURES"
        elif failed:
            status = "FAIL_CLOSED"
        elif len(completed) == len(symbols):
            status = "COMPLETED"
        else:
            status = "CANCELLED"
        state = tracker.state()
        result = {
            "artifact": "ALL_SUMMARY", "mode": ALL_SYMBOLS_ID, "profile": PROFILE,
            "universe_id": universe_id, "symbols": list(symbols),
            "completed_symbols": len(completed), "failed_symbols": len(failed),
            "total_evaluated_configs": total_evaluated,
            "best_positive_net_pnl": state["best_positive_net_pnl"],
            "best_net_pnl_fallback": state["best_net_pnl_fallback"],
            "best_win_count": state["best_win_count"], "positive_net_pnl_found": state["positive_net_pnl_found"],
            "per_symbol": completed, "failed_symbol_reasons": failed,
            "status": status, "started_at": started, "completed_at": _now(),
            "cross_symbol_sample_merge": False, "streaming_memory": "O(1)_BOUNDED_INCUMBENTS",
        }
        self._write(root, "ALL_SUMMARY.json", result)
        self._write(root, "ALL_BEST_CONFIGS.json", {"mode": ALL_SYMBOLS_ID,
                    "best_positive_net_pnl": result["best_positive_net_pnl"],
                    "best_net_pnl_fallback": result["best_net_pnl_fallback"],
                    "best_win_count": result["best_win_count"]})
        self._progress({"artifact": "ALL_SUMMARY", **result, "selected_symbol": ALL_SYMBOLS_ID})
        return result


__all__ = ["AllSymbolsResearchPipeline"]
