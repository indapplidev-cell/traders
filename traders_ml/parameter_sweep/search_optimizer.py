"""Sequential durable suggest/resolve/simulate/observe research campaigns."""
from itertools import product
from math import atan, pi, prod
from pathlib import Path
import json
import time

import optuna
from optuna.trial import TrialState

from .result_search import fingerprint, ResultSearchService, ENGINE_VERSION, ResearchStorageBudgetExceeded
from .locking import SingleRunLock


def objective(result):
    if result.get("blockers") or result.get("result") != "SIMULATED":
        return -2.0
    trades=result.get("closed_trades",[])
    pnl=float(result.get("net_pnl",0))
    winner=any(float(t["net_pnl"])>0 for t in trades)
    # Profit existence dominates all period-PnL tie breaks. Gate counts never score.
    return (2.0 if winner else 0.0)+atan(pnl)/pi


def read_trial(path):
    record=json.loads(path.read_text())
    checksum=record.pop("checksum",None)
    if checksum!=fingerprint(record):raise ValueError("TRIAL_CHECKSUM_MISMATCH")
    return record


class SearchOptimizer:
    def __init__(self, directory: Path, *, identity: dict, domains: dict, baseline: dict,
                 seed: int, mode: str="auto", exhaustive_limit: int=256):
        if not domains or any(not v for v in domains.values()):
            raise ValueError("NONEMPTY_FINITE_DOMAINS_REQUIRED")
        if mode not in ("auto","exhaustive","tpe"):
            raise ValueError("UNKNOWN_OPTIMIZER_MODE")
        self.directory=directory
        self.domains={k:list(dict.fromkeys(v)) for k,v in sorted(domains.items())}
        self.baseline=baseline
        if any(k not in baseline or baseline[k] not in v for k,v in self.domains.items()):
            raise ValueError("BASELINE_MUST_BE_IN_DOMAINS")
        size=prod(len(v) for v in self.domains.values())
        self.mode=("exhaustive" if size<=exhaustive_limit else "tpe") if mode=="auto" else mode
        if self.mode=="exhaustive" and size>100000:
            raise ValueError("EXHAUSTIVE_SPACE_LIMIT_EXCEEDED")
        self.seed=seed
        self.manifest={"schema":"research-optimizer/1","identity":identity,"domains":self.domains,
            "baseline":baseline,"seed":seed,"mode":self.mode,"engine":ENGINE_VERSION,
            "optuna":optuna.__version__,"workers":1,"space_size":size,
            "sampler":"TPESampler seed=(seed+trial_number) mod 2**32; n_startup_trials=3",
            "objective":"invalid=-2; valid=2*has_positive_closed_net_trade+atan(period_net_pnl)/pi",
            "tie_break":"objective descending, configuration fingerprint ascending"}
        self.manifest["fingerprint"]=fingerprint(self.manifest)

    def run(self, evaluator, validator, *, max_trials, max_wall_time, storage_budget_bytes,
            artifact_budget_bytes=None, cancel=lambda:False, on_result=None, artifacts=None, finalize=None):
        if max_trials<1 or max_wall_time<=0 or storage_budget_bytes<4096:
            raise ValueError("INVALID_SEARCH_BUDGET")
        artifact_budget_bytes=artifact_budget_bytes or storage_budget_bytes
        self.directory.mkdir(parents=True,exist_ok=True)
        with SingleRunLock(self.directory/"RUN.lock",self.manifest["fingerprint"]):
            path=self.directory/"OPTIMIZER_MANIFEST.json"
            if path.exists():
                if json.loads(path.read_text())!=self.manifest:
                    raise ValueError("INCOMPATIBLE_OPTIMIZER_RESUME")
            else:
                ResultSearchService._write(path,self.manifest)
            for name, value in (artifacts or {}).items():
                artifact = self.directory/name
                if artifact.exists() and json.loads(artifact.read_text()) != value:
                    raise ValueError("INCOMPATIBLE_CAMPAIGN_ARTIFACT:"+name)
                ResultSearchService._write(artifact,value)
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            study=optuna.create_study(storage="sqlite:///"+(self.directory/"study.sqlite3").resolve().as_posix(),
                study_name=self.manifest["fingerprint"],load_if_exists=True,direction="maximize")
            try:
                try:
                    result=self._loop(study,evaluator,validator,max_trials,max_wall_time,storage_budget_bytes,
                                      artifact_budget_bytes,cancel,on_result)
                except ResearchStorageBudgetExceeded:
                    result={'outcome':'STORAGE_BUDGET','found':False,
                        'completed_trials':len(study.get_trials(states=(TrialState.COMPLETE,)))}
                return finalize(result) if finalize else result
            finally:
                study._storage.remove_session()
                backend=getattr(study._storage,"_backend",study._storage)
                if hasattr(backend,"engine"): backend.engine.dispose()

    def _loop(self,study,evaluator,validator,max_trials,max_wall,budget,artifact_budget,cancel,on_result):
        started=time.monotonic()
        checkpoint=self.directory/"OPTIMIZER_STATUS.json"
        elapsed=json.loads(checkpoint.read_text()).get("elapsed_seconds",0) if checkpoint.exists() else 0
        for completed_trial in study.get_trials(deepcopy=False,states=(TrialState.COMPLETE,)):
            saved=read_trial(self.directory/f"trial_{completed_trial.number:06d}.json")
            if saved["objective"]!=completed_trial.value or saved["configuration_hash"]!=completed_trial.user_attrs.get("configuration_hash"):
                raise ValueError("TRIAL_LEDGER_MISMATCH")
            if on_result and on_result(saved):
                finished=study.get_trials(states=(TrialState.COMPLETE,))
                result={'outcome':'CANDIDATE_HANDOFF','completed_trials':len(finished),
                    'unique_configurations':len({t.user_attrs.get('configuration_hash') for t in finished}),
                    'unique_behaviors':len({t.user_attrs.get('behavior_hash') for t in finished}),
                    'elapsed_seconds':elapsed+time.monotonic()-started,'found':False,'manifest_fingerprint':self.manifest['fingerprint']}
                ResultSearchService._write(checkpoint,result)
                return result
        keys=list(self.domains)
        baseline={k:self.baseline[k] for k in keys}
        grid=None
        if self.mode=="exhaustive":
            grid=[baseline]+[dict(zip(keys,values)) for values in product(*(self.domains[k] for k in keys))
                            if dict(zip(keys,values))!=baseline]
        outcome="NOT_FOUND_WITHIN_BUDGET"
        while True:
            trials=study.get_trials(deepcopy=False)
            completed=[t for t in trials if t.state==TrialState.COMPLETE]
            if cancel(): outcome="CANCELLED"; break
            pending=[t for t in trials if t.state in (TrialState.RUNNING,TrialState.WAITING)]
            if len(trials)>=max_trials and not pending: break
            if elapsed+time.monotonic()-started>=max_wall: outcome="WALL_TIME_BUDGET"; break
            if sum(p.stat().st_size for p in self.directory.rglob('*') if p.is_file())+32768>=budget:
                outcome="STORAGE_BUDGET"; break
            running=[t for t in trials if t.state==TrialState.RUNNING]
            if len(running)>1: raise ValueError("MULTIPLE_RUNNING_TRIALS_IN_SINGLE_WORKER_STUDY")
            if running:
                trial=optuna.trial.Trial(study,running[0]._trial_id)
            else:
                if grid is not None and len(trials)>=len(grid) and not pending: outcome="SEARCH_SPACE_EXHAUSTED"; break
                number=len(trials)
                fixed=(None if pending else grid[number] if grid is not None else baseline if number==0 else
                       {k:self.domains[k][0 if number==1 else -1] for k in keys} if number in (1,2) else None)
                if fixed is not None and not any(t.state==TrialState.WAITING for t in trials): study.enqueue_trial(fixed)
                trial=study.ask()
            number=trial.number
            study.sampler=optuna.samplers.TPESampler(seed=(self.seed+number)%2**32,n_startup_trials=3)
            proposal={k:trial.suggest_categorical(k,v) for k,v in self.domains.items()}
            result_path=self.directory/f"trial_{number:06d}.json"
            if result_path.exists():
                record=read_trial(result_path)
                if record["proposal"]!=proposal: raise ValueError("RECOVERED_TRIAL_PROPOSAL_MISMATCH")
            else:
                try:
                    resolved=validator(proposal)
                    config_hash=fingerprint(resolved)
                except (ValueError,TypeError) as error:
                    resolved=None;config_hash=fingerprint(proposal)
                    result={"result":"INVALID_CONFIGURATION","blockers":[{"reason":str(error)}]}
                else:
                    duplicate=next((t for t in completed if t.user_attrs.get("configuration_hash")==config_hash),None)
                    if duplicate:
                        result=read_trial(self.directory/f"trial_{duplicate.number:06d}.json")["result"]
                    else: result=evaluator(proposal)
                if any(b.get("reason")=="TRIAL_INTERRUPTED_BY_BUDGET_OR_CANCEL" for b in result.get("blockers",[])):
                    outcome="CANCELLED" if cancel() else "WALL_TIME_BUDGET"
                    break
                record={"number":number,"proposal":proposal,"resolved":resolved,"configuration_hash":config_hash,
                        "result":result,"objective":objective(result)}
                record["checksum"]=fingerprint(record)
                encoded=json.dumps(record,sort_keys=True,indent=2).encode()
                used=sum(p.stat().st_size for p in self.directory.rglob('*') if p.is_file())
                artifact_used=sum(p.stat().st_size for p in self.directory.glob('trial_*.json'))
                if used+len(encoded)+32768>budget or artifact_used+len(encoded)>artifact_budget:
                    outcome="STORAGE_BUDGET"; break
                ResultSearchService._write(result_path,record)
            trial.set_user_attr("configuration_hash",record["configuration_hash"])
            behavior=fingerprint({k:record["result"].get(k) for k in ("events","closed_trades","blockers")})
            trial.set_user_attr("behavior_hash",behavior)
            study.tell(trial,record["objective"])
            ResultSearchService._write(checkpoint,{"elapsed_seconds":elapsed+time.monotonic()-started,
                "completed_trials":len(completed)+1,"outcome":"RUNNING"})
            if on_result and on_result(record): outcome="CANDIDATE_HANDOFF"; break
        finished=study.get_trials(deepcopy=False)
        result={"outcome":outcome,"elapsed_seconds":elapsed+time.monotonic()-started,
            "completed_trials":sum(t.state==TrialState.COMPLETE for t in finished),
            "unique_configurations":len({t.user_attrs.get("configuration_hash") for t in finished if t.state==TrialState.COMPLETE}),
            "unique_behaviors":len({t.user_attrs.get("behavior_hash") for t in finished if t.state==TrialState.COMPLETE}),
            "found":False,"manifest_fingerprint":self.manifest["fingerprint"]}
        ResultSearchService._write(checkpoint,result)
        return result
