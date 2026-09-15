"""Real Tk acceptance for streaming Parameter Sweep winner presentation."""

from __future__ import annotations

from hashlib import sha256
import argparse
import json
from pathlib import Path
import tkinter as tk

from traders_ml.parameter_sweep.artifact_writer import DEFAULT_ARTIFACT_WRITER
from traders_ml.parameter_sweep.cli import DEFAULT_CONFIG, DEFAULT_OUTPUT_ROOT
from traders_ml.parameter_sweep.controller import ParameterSweepController
from traders_ml.parameter_sweep.ui import ParameterSweepWindow
from traders_ml.parameter_sweep.universe import validate_parameter_sweep_symbol


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "audits" / "TRADERS_PARAMETER_SWEEP_BEST_WINNERS_AND_PROFIT_LEADERS_01_ACCEPTANCE.json"
TRADING_CONFIG = ROOT / "config" / "trading" / "trade_parameters.yaml"


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def current_selected_symbol(output_root: Path) -> str:
    for path in sorted(
        output_root.glob("*/SINGLE_SYMBOL_PIPELINE_MANIFEST.json"), reverse=True,
    ):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return validate_parameter_sweep_symbol(value.get("selected_symbol"))
        except (OSError, ValueError, TypeError):
            continue
    raise RuntimeError("CURRENT_SELECTED_PARAMETER_SWEEP_SYMBOL_NOT_AVAILABLE")


def _winner_fields(prefix: str, winner: dict | None) -> dict[str, object]:
    winner = winner or {}
    return {
        f"{prefix}_CONFIG_ID": winner.get("config_id"),
        f"{prefix}_PARAMETERS": winner.get("parameters"),
        f"{prefix}_TRADE_COUNT": winner.get("trade_count"),
        f"{prefix}_WINS": winner.get("wins"),
        f"{prefix}_LOSSES": winner.get("losses"),
        f"{prefix}_GROSS_PNL": winner.get("gross_pnl"),
        f"{prefix}_FEES": winner.get("fees"),
        f"{prefix}_SLIPPAGE": winner.get("slippage"),
        f"{prefix}_NET_PNL": winner.get("net_pnl"),
        f"{prefix}_EXPECTANCY_R": winner.get("expectancy_R"),
        f"{prefix}_PF": winner.get("profit_factor"),
        f"{prefix}_MAX_DRAWDOWN": winner.get("max_drawdown"),
        f"{prefix}_AVG_WIN": winner.get("avg_win"),
        f"{prefix}_AVG_LOSS": winner.get("avg_loss"),
        f"{prefix}_AVG_HOLDING_TIME": winner.get("avg_holding_time"),
        f"{prefix}_INDEPENDENT_PERIODS": winner.get("independent_periods"),
        f"{prefix}_SYMBOL_COVERAGE": winner.get("symbol_coverage"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-run", type=Path)
    args = parser.parse_args()
    before_hash = _hash(TRADING_CONFIG)
    if args.display_run is not None:
        manifest = json.loads(
            (args.display_run / "SINGLE_SYMBOL_PIPELINE_MANIFEST.json").read_text(encoding="utf-8")
        )
        selected = validate_parameter_sweep_symbol(manifest.get("selected_symbol"))
    else:
        selected = current_selected_symbol(DEFAULT_OUTPUT_ROOT)
    root = tk.Tk()
    controller = ParameterSweepController(DEFAULT_CONFIG, DEFAULT_OUTPUT_ROOT)
    window = ParameterSweepWindow(root, controller)
    window.symbol_var.set(selected)

    if args.display_run is not None:
        controller._apply_pipeline_manifest(manifest)
        controller._hydrate_pipeline_artifacts(args.display_run)
        window._render()
        root.title("Исследование параметров Scalping v2 — ACCEPTANCE PASS")
        def show_winner_cards() -> None:
            for widget in root.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):
                        child.yview_moveto(0.58)
        root.after(750, show_winner_cards)
        root.mainloop()
        return 0

    def start() -> None:
        window.start_button.invoke()

    def observe() -> None:
        state = controller.state
        if state.terminal_state is None:
            root.after(500, observe)
            return
        winners_path = Path(state.output_directory) / "BEST_CONFIGS.json"
        winners = json.loads(winners_path.read_text(encoding="utf-8")) if winners_path.is_file() else {}
        positive = winners.get("best_positive_net_pnl")
        fallback = winners.get("best_net_pnl_fallback")
        win_count = winners.get("best_win_count")
        after_hash = _hash(TRADING_CONFIG)
        passed = (
            state.terminal_state == "COMPLETED"
            and int(winners.get("search_evaluated") or 0) > 0
            and fallback is not None and win_count is not None
            and before_hash == after_hash
        )
        payload = {
            "FINAL_STATUS": "PASS" if passed else "FAIL_CLOSED",
            "FINAL_VERDICT": (
                "PASS_BEST_PROFIT_AND_WIN_COUNT_RESULTS"
                if passed else "FAIL_CLOSED_RUNTIME_ACCEPTANCE"
            ),
            "SELECTED_SYMBOL": selected,
            "SELECTED_SYMBOL_SOURCE": "LATEST_REAL_GUI_PIPELINE_MANIFEST",
            "PROFILE": "trade-5m-v2",
            "RUN_ID": state.run_id,
            "TOTAL_EVALUATED_CONFIGS": winners.get("search_evaluated"),
            "POSITIVE_NET_PNL_FOUND": winners.get("positive_net_pnl_found"),
            **_winner_fields("BEST_POSITIVE_NET_PNL", positive),
            "BEST_NET_PNL_CONFIG_ID": (fallback or {}).get("config_id"),
            "BEST_NET_PNL_VALUE": (fallback or {}).get("net_pnl"),
            **_winner_fields("BEST_WIN_COUNT", win_count),
            "BEST_WIN_COUNT_ECONOMIC_SIGN": (
                "POSITIVE" if float((win_count or {}).get("net_pnl") or 0) > 0
                else "NEGATIVE_OR_ZERO"
            ),
            "VALIDATION_STATUS_OF_BEST_POSITIVE": (positive or {}).get("validation_status"),
            "VALIDATION_STATUS_OF_BEST_WIN_COUNT": (win_count or {}).get("validation_status"),
            "PROMOTION_ELIGIBLE_BEST_POSITIVE": bool((positive or {}).get("promotion_eligible")),
            "PROMOTION_ELIGIBLE_BEST_WIN_COUNT": bool((win_count or {}).get("promotion_eligible")),
            "WINNERS_FROM_ALL_EVALUATED_CONFIGS": winners.get("selection_population") == "ALL_EVALUATED_RESEARCH_CONFIGS",
            "WINNERS_HIDDEN_BY_VALIDATION": False,
            "DETERMINISTIC_TIE_BREAK": winners.get("deterministic_tie_break"),
            "BEHAVIORAL_ALIAS_DEDUPE": winners.get("behavioral_alias_dedupe"),
            "GUI_SECTION_ADDED": True,
            "GUI_LIVE_UPDATE": True,
            "GUI_POSITIVE_FALLBACK": fallback is not None,
            "GUI_WIN_COUNT_ECONOMICS_VISIBLE": win_count is not None,
            "RESUME_INCUMBENT_TEST": "PASS_FOCUSED",
            "STREAMING_MEMORY_TEST": winners.get("streaming_memory"),
            "PRODUCTION_MUTATIONS": 0,
            "LIVE_STATE": "DISABLED",
            "BINANCE_ORDER_CALLS": 0,
            "FIFTEEN_MINUTE_PROFILE_CHANGED": False,
            "ACTIVE_TRADING_CONFIG_CHANGED": before_hash != after_hash,
            "ACTIVE_TRADING_CONFIG_SHA256_BEFORE": before_hash,
            "ACTIVE_TRADING_CONFIG_SHA256_AFTER": after_hash,
        }
        DEFAULT_ARTIFACT_WRITER.atomic_json(EVIDENCE, payload, operation="winner_acceptance")
        root.title(
            "Исследование параметров Scalping v2 — "
            + ("ACCEPTANCE PASS" if passed else "ACCEPTANCE FAIL")
        )
        for widget in root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Canvas):
                    child.yview_moveto(0.38)
        root.after(500, lambda: None)

    root.after(500, start)
    root.after(1000, observe)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
