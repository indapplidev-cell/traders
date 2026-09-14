"""Durable candidate verification and complete, inactive YAML exports."""
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import yaml

from app.config.trade_parameters import load_trade_parameters
from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .result_search import ENGINE_VERSION, ResultSearchService, fingerprint, ResearchStorageBudgetExceeded
from .frozen_funnel import resolve_frozen_configuration
from .search_history import HistoryProvider
from .chronological_search import simulate


def flatten(value, prefix=''):
    result={}
    for key,item in value.items():
        name=prefix+key
        if isinstance(item,dict):result.update(flatten(item,name+'.'))
        else:result[name]=item
    return result


def export_configuration(frozen, overrides):
    baseline=resolve_frozen_configuration(frozen,{}).parameters.model_dump(mode='json')
    risk=baseline.pop('risk')
    return {'schema_version':1,'config_version':'inactive-research-export-1',
        'profiles':{'trade-5m-v2':baseline,'trade-15m-v1':{'enabled':False}},
        'scalping_v2':{'parameter_sets':{
            'baseline':{'id':'research-frozen-baseline','label':'Frozen source baseline','version':'1','inherits':None,
                'overrides':{'risk.'+k:v for k,v in flatten(risk).items()}},
            'candidate':{'id':'research-candidate','label':'Inactive research candidate','version':'1',
                'inherits':'research-frozen-baseline','overrides':overrides}},
            'paper':{'previous_parameter_set':'research-frozen-baseline','active_parameter_set':'research-candidate',
                'switched_at_utc':'FROZEN_RESEARCH','activation_cycle_boundary_ms':0,
                'activation_revision':'INACTIVE_EXPORT','activation_reason':'OFFLINE_REPLAY_ONLY'}}}


def load_export(path, frozen):
    loaded=load_trade_parameters(path).resolve_scalping_v2_parameter_set(
        frozen_source_authority_hash=frozen['resolved_config_hash'])
    # The production loader/resolver owns parsing, inheritance, risk and validation.
    # Historical runner retains source set identity for the frozen statistics scope.
    values=loaded.parameters.model_dump(mode='json')
    flat={}
    for key in frozen['parameters']:
        item=values
        for part in key.split('.'):item=item[part]
        flat[key]=item
    resolved=resolve_frozen_configuration(frozen,flat)
    if loaded.resolved_config_hash!=resolved.resolved_config_hash:
        raise ValueError('EXPORTED_RESOLVED_HASH_MISMATCH')
    return resolved


def validate_result(result, *, dataset_hash, config_hash, quality):
    if (result.get('engine')!=ENGINE_VERSION or result.get('dataset_fingerprint')!=dataset_hash or
        result.get('configuration_fingerprint')!=config_hash):raise ValueError('EVIDENCE_IDENTITY_MISMATCH')
    if result.get('quality')!=quality:raise ValueError('EVIDENCE_QUALITY_MISMATCH')
    if quality=='HISTORICAL_VERIFIED' and result.get('execution_assumptions') is not None:
        raise ValueError('ASSUMPTIONS_CANNOT_BE_HISTORICALLY_VERIFIED')
    if result.get('result')!='SIMULATED' or result.get('blockers') or result.get('open_positions'):
        raise ValueError('INCOMPLETE_OR_INVALID_REPLAY')
    trades=result.get('closed_trades',[])
    if len({t['identity'] for t in trades})!=len(trades):raise ValueError('DUPLICATE_TRADE_IDENTITY')
    winners=[]
    for t in trades:
        gross,entry_fee,exit_fee,net=map(Decimal,(t['gross_pnl'],t['entry_fee'],t['exit_fee'],t['net_pnl']))
        if not all(v.is_finite() for v in (gross,entry_fee,exit_fee,net)) or min(entry_fee,exit_fee)<0:
            raise ValueError('INVALID_COST_ACCOUNTING')
        if abs(gross-entry_fee-exit_fee-net)>Decimal('0.00000001'):raise ValueError('NET_ACCOUNTING_MISMATCH')
        if t['exit_cause'] not in ('STOP_LOSS','TAKE_PROFIT') or t['exit_boundary']<=t['entry_boundary']:
            raise ValueError('INVALID_CLOSED_TRADE_PATH')
        admission=next((x for x in t['trace'] if x['event']=='CAUSAL_ADMISSION'),None)
        if (not admission or admission['dataset_fingerprint']!=dataset_hash or
            admission['configuration_fingerprint']!=config_hash or admission['decision_boundary']>t['entry_boundary']):
            raise ValueError('MISSING_CAUSAL_ADMISSION')
        if net>0:winners.append(t)
    if abs(sum((Decimal(t['net_pnl']) for t in trades),Decimal(0))-Decimal(result['net_pnl']))>Decimal('0.00000001'):
        raise ValueError('PERIOD_PNL_MISMATCH')
    if not winners:raise ValueError('NO_POSITIVE_CLOSED_NET_TRADE')
    return winners


class FindingVerifier:
    def __init__(self, directory, dataset, request, *, replay=None, should_stop=lambda:False):
        self.directory,self.dataset,self.request=Path(directory),Path(dataset),request
        self.manifest,rows=HistoryProvider.load(self.dataset)
        self.frozen=next(r['frozen'] for r in rows if r['kind']=='PERSISTED_BOUNDARY')
        self.replay=replay or (lambda overrides:simulate(self.dataset,overrides,request.initial_capital,should_stop=should_stop))
        self.should_stop=should_stop

    def _bytes(self,path,content):
        files=[p for p in self.directory.rglob('*') if p.is_file() and p!=path]
        used=sum(p.stat().st_size for p in files)
        artifacts=sum(p.stat().st_size for p in files if not p.name.startswith('study.sqlite3'))
        if (used+len(content)+32768>getattr(self.request,'storage_budget_bytes',128000000) or
            artifacts+len(content)+32768>getattr(self.request,'artifact_budget_bytes',64000000)):
            raise ResearchStorageBudgetExceeded('FINDING_STORAGE_BUDGET')
        DEFAULT_ARTIFACT_WRITER.atomic_bytes(path,content)

    def _write(self,path,value):
        self._bytes(path,json.dumps(value,sort_keys=True,indent=2,allow_nan=False).encode())

    def published(self):
        path=self.directory/'SUCCESSFUL_CONFIGS.json'
        entries=json.loads(path.read_text()) if path.exists() else []
        for entry in entries:
            for name,digest in entry['files'].items():
                if sha256((self.directory/name).read_bytes()).hexdigest()!=digest:
                    raise ValueError('PUBLISHED_FINDING_CHECKSUM_MISMATCH')
            key=entry['configuration']
            proof=json.loads((self.directory/f'proof_{key}.json').read_text())
            result=json.loads((self.directory/f'result_{key}.json').read_text())
            winners=validate_result(result,dataset_hash=self.manifest['fingerprint'],config_hash=key,quality=self.request.data_mode)
            if (not proof.get('verified') or fingerprint(result)!=proof['replay_fingerprint'] or
                entry['net_pnl']!=result['net_pnl'] or entry['wins']!=len(winners) or
                entry['losses']!=sum(Decimal(t['net_pnl'])<0 for t in result['closed_trades']) or
                entry['scope']!=self.request.scope or entry['symbols']!=list(self.request.symbols)):
                raise ValueError('PUBLISHED_FINDING_PROOF_MISMATCH')
        return entries

    def discover(self,overrides,trade):
        resolved=resolve_frozen_configuration(self.frozen,overrides)
        key=resolved.resolved_config_hash
        path=self.directory/f'candidate_{key}.json'
        if not path.exists():
            self._write(path,{'phase':'FOUND_CANDIDATE','configuration':key,'overrides':overrides,
                'first_profitable_close':trade,'dataset':self.manifest['fingerprint'],'engine':ENGINE_VERSION})

    def accept(self,record):
        entries=self.published()
        if len(entries)>=self.request.target_config_count:return True
        result=record['result']
        if not any(Decimal(t['net_pnl'])>0 for t in result.get('closed_trades',[])):return False
        resolved=resolve_frozen_configuration(self.frozen,record['proposal'])
        key=resolved.resolved_config_hash
        try:
            winners=validate_result(result,dataset_hash=self.manifest['fingerprint'],config_hash=key,quality=self.request.data_mode)
        except ValueError as error:
            self._write(self.directory/f'rejected_{key}.json',{'reason':str(error),'trial':record['number']})
            return False
        # Identical realized paths are one finding even when inactive knobs differ.
        behavior=fingerprint([{k:v for k,v in t.items() if k not in ('identity','trace','expectancy_money','expectancy_R')} for t in result['closed_trades']])
        if any(e['configuration']==key or e['behavior']==behavior for e in entries):return False
        self.discover(record['proposal'],min(winners,key=lambda t:t['exit_observed_closed_ms']))
        if self.should_stop():return False
        yaml_path=self.directory/f'candidate_{key}.yaml'
        self._bytes(yaml_path,yaml.safe_dump(export_configuration(self.frozen,record['proposal']),sort_keys=False).encode())
        loaded=load_export(yaml_path,self.frozen)
        if loaded.resolved_config_hash!=key:raise ValueError('EXPORTED_CONFIGURATION_DIFFERS')
        loaded_flat=flatten(loaded.parameters.model_dump(mode='json'))
        replay_overrides={k:loaded_flat[k] for k in record['proposal']}
        repeated=self.replay(replay_overrides)
        if self.should_stop():return False
        validate_result(repeated,dataset_hash=self.manifest['fingerprint'],config_hash=key,quality=self.request.data_mode)
        if fingerprint(repeated)!=fingerprint(result):raise ValueError('REPLAY_RESULT_MISMATCH')
        result_path=self.directory/f'result_{key}.json'
        proof_path=self.directory/f'proof_{key}.json'
        self._write(result_path,result)
        self._write(proof_path,{'verified':True,'engine':ENGINE_VERSION,'dataset':self.manifest['fingerprint'],
            'configuration':key,'result_fingerprint':fingerprint(result),'replay_fingerprint':fingerprint(repeated),
            'comparison':'EXACT_CANONICAL_RESULT; ACCOUNTING_TOLERANCE_1E-8','quality':self.request.data_mode,
            'production_loader_and_resolver':'PASS','original_baseline_hash':self.request.baseline_hash,
            'source_authority_hash':self.frozen['resolved_config_hash'],'frozen_baseline':self.frozen})
        entry={'configuration':key,'behavior':behavior,'scope':self.request.scope,'symbols':list(self.request.symbols),
            'quality':self.request.data_mode,'net_pnl':result['net_pnl'],'wins':len(winners),
            'losses':sum(Decimal(t['net_pnl'])<0 for t in result['closed_trades']),
            'first_profitable_close':min(t['exit_observed_closed_ms'] for t in winners),
            'independent_validation':'NOT_EVALUATED','deployment_readiness':'NOT_ESTABLISHED',
            'files':{p.name:sha256(p.read_bytes()).hexdigest() for p in (yaml_path,result_path,proof_path)}}
        entries.append(entry)
        # Index publication is the commit point; no FOUND is visible before it.
        self._write(self.directory/'SUCCESSFUL_CONFIGS.json',entries)
        self.report()
        return len(entries)>=self.request.target_config_count

    def report(self):
        entries=self.published()
        winners=[]
        proofs=[]
        for e in entries:
            result=json.loads((self.directory/f"result_{e['configuration']}.json").read_text())
            winners.extend({'configuration':e['configuration'],**t} for t in result['closed_trades'] if Decimal(t['net_pnl'])>0)
            proofs.append(json.loads((self.directory/f"proof_{e['configuration']}.json").read_text()))
        self._bytes(self.directory/'WINNING_TRADES.jsonl',
            ''.join(json.dumps(t,sort_keys=True)+'\n' for t in winners).encode())
        self._write(self.directory/'REPLAY_PROOF.json',proofs)
        text=f"Verified configurations: {len(entries)}\nScope: {self.request.scope}\nIndependent validation: NOT_EVALUATED\n"
        for e in entries:text+=f"\n{e['configuration']}: period net PnL {e['net_pnl']}; wins {e['wins']}; losses {e['losses']}; quality {e['quality']}\n"
        self._bytes(self.directory/'REPORT.md',text.encode())
        self._write(self.directory/'SUCCESSFUL_CONFIGS.json',entries)
        return entries


def replay_export(directory: Path, candidate: str):
    """Fresh-process entry point: use exported YAML and its frozen manifest."""
    manifest=json.loads((directory/'SEARCH_MANIFEST.json').read_text())
    frozen=manifest['frozen_baseline']
    path=directory/f'candidate_{candidate}.yaml'
    resolved=load_export(path,frozen)
    if resolved.resolved_config_hash!=candidate:raise ValueError('EXPORTED_CONFIGURATION_DIFFERS')
    dataset=Path(manifest['dataset_path'])
    actual,_=HistoryProvider.load(dataset)
    if actual['fingerprint']!=manifest['dataset']:raise ValueError('EXPORTED_DATASET_DIFFERS')
    values=flatten(resolved.parameters.model_dump(mode='json'))
    from .frozen_funnel import SEARCHABLE_PARAMETERS
    result=simulate(dataset,{k:values[k] for k in SEARCHABLE_PARAMETERS},manifest['request']['initial_capital'])
    proof=json.loads((directory/f'proof_{candidate}.json').read_text())
    if fingerprint(result)!=proof['result_fingerprint']:raise ValueError('FRESH_EXPORTED_REPLAY_MISMATCH')
    return {'result':'IDENTICAL_EXPORTED_REPLAY','configuration':candidate,'result_fingerprint':fingerprint(result),
        'net_pnl':result['net_pnl'],'closed_trades':len(result['closed_trades'])}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--candidate',required=True)
    a=p.parse_args()
    print(json.dumps(replay_export(a.directory,a.candidate),indent=2))
