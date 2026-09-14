"""Bounded historical trials: shared funnel, selector and isolated PAPER book."""
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
from decimal import Decimal

from app.engine_paper.eligible_approval_ranking import rank_eligible_candidates
from app.engine_paper.scalping_execution_readiness import check_scalping_execution_readiness
from app.engine_paper.controlled_quantity_validity import calculate_quantity_sizing
from app.engine_safety.paper_domain import PaperDomainError
from .frozen_funnel import FrozenFunnel
from .historical_execution import HistoricalExecution, decimal


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    symbol: str
    ranking: object
    result: object


def simulate(directory: Path, overrides: dict, initial_capital, *, assumed_execution_costs: dict | None = None):
    """Assumptions must be supplied explicitly; never promoted to verified data.

    Exact execution-quantity/exit-time costs are distinct from the admission
    reference-notional snapshot. Missing execution inputs affect admitted paths
    only. The baseline that rejects every plan needs no execution assumptions.
    """
    funnel = FrozenFunnel(directory, overrides)
    if assumed_execution_costs is not None:
        required = {"spread_bps", "depth_impact_bps", "entry_slippage_bps", "exit_slippage_bps",
                    "entry_fee_bps", "exit_fee_bps"}
        if set(assumed_execution_costs) != required or any(
                not decimal(v).is_finite() or decimal(v)<0 for v in assumed_execution_costs.values()):
            raise ValueError("INVALID_EXPLICIT_EXECUTION_ASSUMPTIONS")
    book = HistoricalExecution(initial_capital, funnel.runner.runtime_parameters)
    interval = funnel.manifest["intervals"]
    start, end, tail = interval["search_start_ms"], interval["search_end_ms"], interval["exit_tail_end_ms"]
    candles = {(s,c.open_time_ms):c for s,repo in funnel.repositories.items() for c in repo.rows["1m"]}
    pending = {}
    events, blockers, rejections = [], [], Counter()
    for boundary in range(start, tail+1, 60000):
        for symbol in sorted(tuple(book.positions)):
            p=book.positions[symbol]
            if p.cursor+60000<=boundary:
                c=candles.get((symbol,p.cursor))
                if c is None:
                    blockers.append({"symbol":symbol,"boundary":boundary,"reason":"POSITION_CANDLE_MISSING"})
                    return _result(funnel,book,events,blockers,rejections,assumed_execution_costs)
                book.advance(symbol,c)
        for symbol, candidate in list(pending.items()):
            if candidate.result.closed_until_ms+60000>boundary:
                continue
            del pending[symbol]
            result=candidate.result; plan=result.paper_payload
            costs=assumed_execution_costs
            c=candles.get((symbol,result.closed_until_ms))
            if c is None:
                blockers.append({"symbol":symbol,"boundary":boundary,"reason":"ENTRY_CANDLE_MISSING"})
                continue
            validity=plan.get("paper_context",{}).get("validity_policy") or result.paper_payload.get("validity_policy") or {}
            valid_until=int(validity.get("valid_until_ms",result.closed_until_ms+
                funnel.resolved.parameters.lifecycle.entry_fill_window_seconds*1000))
            if valid_until<c.close_time_ms+1:
                rejections["COMMAND_EXPIRED_BEFORE_ELIGIBLE_CANDLE_CLOSE"]+=1
                continue
            if costs is None:
                blockers.append({"symbol":symbol,"boundary":boundary,
                    "reason":"EXECUTION_QUANTITY_AND_EXIT_TIME_COST_EVIDENCE_REQUIRED"})
                continue
            gate=book.portfolio_gate(result)
            if gate["decision"]!="PASS":
                rejections[gate["reason_code"]]+=1
                continue
            reference=plan["hypothetical_entry_reference"]
            try:
                sizing=calculate_quantity_sizing(symbol=symbol,equity=book.available_capital,
                    entry=decimal(reference),stop=decimal(plan["hypothetical_stop_level"]),
                    risk_per_trade_bps=decimal(book.runtime.risk_per_trade_bps))
            except (ValueError, PaperDomainError) as error:
                rejections[str(error)]+=1
                continue
            decision_time=int(plan["created_at_ms"])
            if decision_time>c.close_time_ms+1:
                rejections["ENTRY_FILL_WINDOW_MISSED"]+=1
                continue
            readiness=check_scalping_execution_readiness(decision_timestamp_ms=result.closed_until_ms,
                now_ms=decision_time,decision_entry=reference,current_price=float(c.open),
                spread_bps=costs["spread_bps"],depth_impact_bps=costs["depth_impact_bps"],
                expected_slippage_bps=costs["entry_slippage_bps"],quantity=float(sizing.normalized_quantity),
                entry_ttl_seconds=funnel.resolved.parameters.lifecycle.entry_fill_window_seconds,
                max_price_drift_bps=funnel.resolved.parameters.lifecycle.maximum_price_drift_bps)
            if not readiness.ready:
                rejections[readiness.reason]+=1
                continue
            impact=decimal(costs["spread_bps"])/2+decimal(costs["depth_impact_bps"])
            try:
                position=book.open(identity=candidate.candidate_id,symbol=symbol,
                    side="LONG" if plan["paper_direction"]=="BULLISH" else "SHORT",reference=reference,
                    stop=plan["hypothetical_stop_level"],target=plan["hypothetical_target_level"],candle=c,
                    entry_fee_bps=costs["entry_fee_bps"],exit_fee_bps=costs["exit_fee_bps"],
                    entry_slippage_bps=decimal(costs["entry_slippage_bps"])+impact,
                    exit_slippage_bps=decimal(costs["exit_slippage_bps"])+impact)
                geometry=plan.get("paper_context",{}).get("scalping_geometry_diagnostics") or {}
                if geometry.get("expected_value_bps") is not None:
                    position.expectancy_money=decimal(reference)*position.quantity*decimal(geometry["expected_value_bps"])/10000
                    position.expectancy_R=position.expectancy_money/position.initial_risk
                position.trace.append({"event":"CAUSAL_ADMISSION","decision_boundary":result.closed_until_ms,
                    "decision_time_ms":decision_time,"dataset_fingerprint":funnel.manifest["fingerprint"],
                    "configuration_fingerprint":funnel.resolved.resolved_config_hash,
                    "market_data":getattr(result,"market_data_payload",{}),
                    "setup_id":plan.get("source_setup_id"),"costs":costs})
            except (ValueError, PaperDomainError) as error:
                rejections[str(error)]+=1
        if boundary>=end or boundary%300000:
            continue
        candidates=[]
        for symbol in funnel.manifest["symbols"]:
            result,cost_blocker,statistics_missing=funnel.run(symbol,boundary)
            plan=result.paper_payload
            diagnostic=plan.get("paper_context",{}).get("scalping_geometry_diagnostics") or {}
            reason=diagnostic.get("rejection_reason") or result.final_reason or result.paper_status
            events.append({"symbol":symbol,"boundary":boundary,"status":result.paper_status,"reason":reason})
            if cost_blocker or statistics_missing or result.error_code:
                blockers.append({"symbol":symbol,"boundary":boundary,
                    "reason":cost_blocker or ("HISTORICAL_STATISTICS_REQUIRED" if statistics_missing else result.error_code)})
                continue
            if result.paper_status!="PAPER_PLAN_READY":
                rejections[str(reason)]+=1
                continue
            gate=book.portfolio_gate(result)
            if gate["decision"]!="PASS":
                rejections[gate["reason_code"]]+=1
                continue
            try:
                calculate_quantity_sizing(symbol=symbol,equity=book.available_capital,
                    entry=decimal(plan["hypothetical_entry_reference"]),stop=decimal(plan["hypothetical_stop_level"]),
                    risk_per_trade_bps=decimal(book.runtime.risk_per_trade_bps))
            except (ValueError,PaperDomainError) as error:
                rejections[str(error)]+=1
                continue
            identity=plan["paper_plan_id"]
            candidates.append(Candidate(identity,symbol,SimpleNamespace(
                risk_score=decimal(result.risk_payload["risk_score"]),planned_risk_reward=decimal(plan["planned_rr"]),
                strategy_score=decimal(result.strategy_payload["strategy_score"]),closed_until_ms=boundary,
                source_run_id=f"research:{boundary}:{symbol}",final_approval_id=identity),result))
        ranked=rank_eligible_candidates(candidates)
        limit=funnel.resolved.parameters.risk.max_new_commands_per_cycle
        for candidate in ranked[:limit]:
            pending[candidate.symbol]=candidate
        rejections["SELECTOR_NOT_SELECTED"]+=max(0,len(ranked)-limit)
    return _result(funnel,book,events,blockers,rejections,assumed_execution_costs)


def _result(funnel,book,events,blockers,rejections,assumptions):
    summary=book.summary()
    if summary["open_positions"]:
        blockers.append({"reason":"INCOMPLETE_EXIT_TAIL","symbols":summary["open_positions"]})
    return {"schema":"chronological-research/1", "dataset_fingerprint":funnel.manifest["fingerprint"],
        "configuration_fingerprint":funnel.resolved.resolved_config_hash,
        "quality":"ASSUMPTION_BASED" if assumptions is not None else "HISTORICAL_VERIFIED",
        "execution_assumptions":assumptions,"blockers":blockers,"events":events,
        "rejections":dict(rejections),"result":"BLOCKED_DATA" if blockers else "SIMULATED",
        "has_profitable_closed_trade":not blockers and any(Decimal(t["net_pnl"])>0 for t in summary["closed_trades"]),**summary}


def main():
    import argparse
    import json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",type=Path,required=True)
    parser.add_argument("--overrides",type=Path,required=True)
    parser.add_argument("--capital",type=Decimal,required=True)
    parser.add_argument("--execution-assumptions",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    result=simulate(args.dataset,json.loads(args.overrides.read_text()),args.capital,
        assumed_execution_costs=json.loads(args.execution_assumptions.read_text()) if args.execution_assumptions else None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    from .result_search import ResultSearchService
    ResultSearchService._write(args.output,result)
    print(json.dumps({k:result[k] for k in ("result","quality","net_pnl","has_profitable_closed_trade")}))
    if result["blockers"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
