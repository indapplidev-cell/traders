from collections import Counter

from .observation_models import RunRecord

REQUIRED_OUTCOMES = ("NO_ACTION", "NO_SETUP", "WAIT", "REJECT", "NO_PLAN", "PAPER_PLAN_READY", "ERROR")


def _distribution(values) -> dict[str, int]:
    result = Counter(str(value) if value is not None else "ABSENT" for value in values)
    return dict(sorted(result.items()))


def analyze_funnel(runs: list[RunRecord], expected_count: int) -> dict:
    distributions = {name: _distribution(getattr(r, name) for r in runs) for name in (
        "status", "final_result", "analysis_status", "setup_status", "strategy_status", "risk_status", "paper_status")}
    for outcome in REQUIRED_OUTCOMES:
        distributions["final_result"].setdefault(outcome, 0)
    funnel = {
        "expected_windows": expected_count,
        "orchestrator_records": len(runs),
        "freshness_passed": sum(r.market_data_freshness_status == "OK" for r in runs),
        "analysis_completed": sum(r.analysis_status not in {None, "ERROR"} for r in runs),
        "setup_result": sum(r.setup_status is not None for r in runs),
        "strategy_result": sum(r.strategy_status is not None for r in runs),
        "risk_result": sum(r.risk_status is not None for r in runs),
        "paper_result": sum(r.paper_status is not None for r in runs),
    }
    stops = Counter()
    for r in runs:
        if r.status.startswith("SKIPPED_"): stops["freshness_or_input"] += 1
        elif r.analysis_status in {None, "ERROR"}: stops["analysis"] += 1
        elif r.setup_status is None: stops["setup"] += 1
        elif r.strategy_status is None: stops["strategy"] += 1
        elif r.risk_status is None: stops["risk"] += 1
        elif r.paper_status is None: stops["paper"] += 1
        else: stops["completed_through_paper"] += 1
    return {"funnel": funnel, "distributions": distributions, "stop_layer_distribution": dict(stops)}
