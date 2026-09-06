"""Portable read-only exact10 historical replay for the 5m shadow profile.

It imports only modules already present in the deployed 15m image, so it can be
streamed into that container without copying or replacing it. It never creates
online runs, PAPER plans, approvals, commands, orders or positions.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path("/service")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_analysis.analysis_snapshot_store import AnalysisSnapshotStore
from app.engine_analysis.market_data_adapter import MarketDataAdapter
from app.engine_analysis.online_config import OnlineAnalysisConfig
from app.engine_analysis.online_runner import OnlineAnalysisRunner
from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_market_data.market_data_snapshot import MarketDataSnapshot
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_risk.risk_runner import RiskRunner
from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_runner import SetupRunner
from app.engine_setup.setup_store import SetupStore
from app.engine_strategy.strategy_runner import StrategyRunner
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE


PROFILE_ID = "trade-5m-v2"
TRIGGER_TIMEFRAME = "5m"
CONTEXT_TIMEFRAMES = ("15m", "1h", "4h")
ANALYSIS_HISTORY = 288


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only exact10 5m shadow replay")
    parser.add_argument("--boundaries-per-symbol", type=int, default=12)
    return parser


def _context_last_open(timeframe: str, boundary: int) -> int:
    duration = timeframe_to_milliseconds(timeframe)
    return boundary // duration * duration - duration


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.boundaries_per_symbol <= 48:
        raise SystemExit("boundaries-per-symbol must be in [1, 48]")
    repository = CandleRepository(create_market_data_session_factory())
    counts = Counter()
    identities: set[tuple[str, str, int]] = set()
    errors: list[dict[str, object]] = []
    planned_rr: list[object] = []
    cost_diagnostics = 0
    symbols = tuple(PREPARED_NEXT_TRADING_UNIVERSE.symbols)
    for symbol in symbols:
        analysis_runner = OnlineAnalysisRunner(
            OnlineAnalysisConfig(
                symbols=[symbol], timeframes=[TRIGGER_TIMEFRAME],
                required_history_candles=ANALYSIS_HISTORY,
                max_snapshot_age_ms=10**15,
            ),
            MarketDataAdapter(), AnalysisSnapshotStore(),
        )
        setup_runner = SetupRunner(SetupDetector(), SetupStore())
        strategy_runner = StrategyRunner()
        risk_runner = RiskRunner()
        boundaries = repository.get_candles(symbol, TRIGGER_TIMEFRAME, limit=args.boundaries_per_symbol)
        for boundary_candle in boundaries:
            if not boundary_candle.is_closed:
                errors.append({"symbol": symbol, "code": "UNCLOSED_5M_CANDLE"})
                continue
            boundary = int(boundary_candle.close_time_ms) + 1
            identity = (PROFILE_ID, symbol, boundary)
            if identity in identities:
                errors.append({"symbol": symbol, "boundary": boundary, "code": "DUPLICATE_PROFILE_BOUNDARY"})
                continue
            identities.add(identity)
            context_ok = True
            for timeframe in CONTEXT_TIMEFRAMES:
                context = repository.get_candles(
                    symbol, timeframe, end_time_ms=_context_last_open(timeframe, boundary), limit=1
                )
                if not context or not context[-1].is_closed or int(context[-1].close_time_ms) >= boundary:
                    context_ok = False
                    errors.append({"symbol": symbol, "boundary": boundary, "code": f"{timeframe}:FUTURE_OR_MISSING_CONTEXT"})
            candles = repository.get_candles(
                symbol, TRIGGER_TIMEFRAME,
                end_time_ms=_context_last_open(TRIGGER_TIMEFRAME, boundary),
                limit=ANALYSIS_HISTORY,
            )
            if len(candles) < ANALYSIS_HISTORY or any(
                not item.is_closed or int(item.close_time_ms) >= boundary for item in candles
            ):
                errors.append({"symbol": symbol, "boundary": boundary, "code": "5m:INSUFFICIENT_OR_FUTURE_DATA"})
                continue
            if not context_ok:
                continue
            snapshot = MarketDataSnapshot(
                symbol=symbol, timeframe=TRIGGER_TIMEFRAME, closed_until_ms=boundary,
                candles=candles, source="postgres", has_gaps=False,
                future_bars_used=False, health_status="OK", enough_data=True,
            )
            analysis = analysis_runner.analyze_market_data_snapshot(snapshot)
            setup = setup_runner.process_analysis_snapshot(analysis)
            strategy = strategy_runner.process_setup_candidate(setup)
            risk = risk_runner.process_strategy_decision(strategy)
            counts["opportunities"] += 1
            counts["analysis"] += int(getattr(analysis, "status", None) == "ANALYZED")
            counts["setups"] += int(getattr(setup, "status", None) == "SETUP_CANDIDATE")
            counts["strategy_approvals"] += int(getattr(strategy, "decision_status", None) == "ALLOW_RESEARCH_TRADE_PLAN")
            counts["risk_approvals"] += int(getattr(risk, "risk_status", None) in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"})
            counts["final_approval_candidates"] += int(getattr(risk, "risk_status", None) in {"RISK_PRE_APPROVED_RESEARCH", "RISK_APPROVED"})
            rr = getattr(setup, "planned_rr", None)
            if rr is not None:
                planned_rr.append(str(rr))
            cost_diagnostics += 1
    expected = len(symbols) * args.boundaries_per_symbol
    payload = {
        "trade_profile_id": PROFILE_ID,
        "trigger_timeframe": TRIGGER_TIMEFRAME,
        "profile_mode": "SHADOW_SEARCH",
        "symbols": list(symbols),
        "boundaries_per_symbol_requested": args.boundaries_per_symbol,
        "expected_opportunities": expected,
        "unique_profile_boundaries": len(identities),
        "counts": dict(counts),
        "planned_rr": planned_rr,
        "cost_diagnostic_count": cost_diagnostics,
        "higher_timeframe_context_closed_only": True,
        "future_candle_usage": 0 if not any("FUTURE" in str(item.get("code")) for item in errors) else 1,
        "paper_command_creation_enabled": False,
        "position_opening_enabled": False,
        "profitability_claimed": False,
        "errors": errors,
    }
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0 if len(identities) == expected and counts["opportunities"] == expected and not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
