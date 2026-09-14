"""Internal real-history campaign entry point over shared research services."""
from pathlib import Path
import json
import time

from .result_search import SearchRequest, ResultSearchService, ENGINE_VERSION
from .search_parameters import generate_space,SPECS
from .search_history import HistoryProvider
from .frozen_funnel import resolve_frozen_configuration, _FrozenOrchestratorConfig
from app.engine_orchestrator.runtime_parameters import _runtime_parameters
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from .opportunity_registry import ResearchOpportunityRegistry
from .chronological_search import simulate
from .search_optimizer import SearchOptimizer


def run_campaign(request: SearchRequest,dataset: Path,output: Path,*,mode="auto",cancel=lambda:False,on_result=None):
    manifest,rows=HistoryProvider.load(dataset)
    interval=manifest["intervals"]
    if (sorted(request.symbols)!=sorted(manifest["symbols"]) or
        int(request.start.timestamp()*1000)!=interval["search_start_ms"] or
        int(request.end.timestamp()*1000)!=interval["search_end_ms"] or
        int(request.data_cutoff.timestamp()*1000)!=interval["data_cutoff_ms"]):
        raise ValueError("REQUEST_DATASET_INTERVAL_OR_SYMBOL_MISMATCH")
    if request.constraints:
        raise ValueError("UNSUPPORTED_CUSTOM_CONSTRAINT_SYNTAX")
    space=generate_space(dataset)
    frozen=next(r["frozen"] for r in rows if r["kind"]=="PERSISTED_BOUNDARY")
    domains=space["domains"]
    specs={s.key:s for s in SPECS}
    if request.parameters:
        domains={}
        for k,values in request.parameters.items():
            if k not in specs:raise ValueError("UNSUPPORTED_PARAMETER:"+k)
            spec=specs[k]
            values=list(values)
            for v in values:
                if isinstance(v,(bool,str)) or not spec.lower<=v<=spec.upper or (spec.value_type=="int" and int(v)!=v):
                    raise ValueError("INVALID_DOMAIN_VALUE:"+k)
            domains[k]=list(dict.fromkeys([frozen["parameters"][k]]+values))
    def validator(proposal):
        resolved=resolve_frozen_configuration(frozen,proposal)
        config=_FrozenOrchestratorConfig(resolved.parameters,symbols=request.symbols,trade_profile_id=request.profile)
        runtime=_runtime_parameters(config.trade_profile,resolved)
        # Construction enforces the actual consumer's conditional/discrete rules.
        # Explicit isolated sources prevent production registry/network defaults.
        ScalpingPaperRunner(runtime_parameters=runtime,scalping_parameters=resolved.parameters,
            cost_source=object(),statistics_source=object(),opportunity_registry=ResearchOpportunityRegistry())
        return {"parameters":resolved.parameters.model_dump(mode="json"),"hash":resolved.resolved_config_hash}
    optimizer=SearchOptimizer(output,identity={"request":request.identity,"dataset":manifest["fingerprint"],
        "space":space["fingerprint"],"baseline":request.baseline_hash,"engine":ENGINE_VERSION},
        domains=domains,baseline={k:frozen["parameters"][k] for k in domains},seed=request.seed,mode=mode)
    prior=output/"OPTIMIZER_STATUS.json"
    used=json.loads(prior.read_text()).get("elapsed_seconds",0) if prior.exists() else 0
    deadline=time.monotonic()+max(0,request.max_wall_time-used)
    return optimizer.run(lambda p:simulate(dataset,p,request.initial_capital,
        should_stop=lambda:cancel() or time.monotonic()>=deadline),validator,max_trials=request.max_trials,
        max_wall_time=request.max_wall_time,storage_budget_bytes=request.storage_budget_bytes,
        artifact_budget_bytes=request.artifact_budget_bytes,cancel=cancel,on_result=on_result,
        artifacts={"GENERATED_SPACE.json":space,"REQUEST.json":request.model_dump(mode="json")})


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request",type=Path,required=True)
    p.add_argument("--dataset",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--mode",choices=("auto","tpe","exhaustive"),default="auto")
    a=p.parse_args()
    request=SearchRequest.model_validate_json(a.request.read_text())
    print(json.dumps(run_campaign(request,a.dataset,a.output,mode=a.mode),indent=2))


if __name__=="__main__":main()
