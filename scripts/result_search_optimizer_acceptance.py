"""Installed, bounded real-history optimizer and resume acceptance."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from app.config.trade_parameters import CONFIG_PATH
from traders_ml.parameter_sweep.generated_search import run_campaign
from traders_ml.parameter_sweep.result_search import SearchRequest, deployment_diagnostics
from traders_ml.parameter_sweep.search_optimizer import read_trial


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    request=SearchRequest.model_validate_json(Path('docs/audits/BLOCK_02_REQUEST.json').read_text())
    request=request.model_copy(update={'max_trials':5,'max_wall_time':600.0})
    before=sha256(CONFIG_PATH.read_bytes()).hexdigest()
    result=run_campaign(request,a.dataset,a.output,mode='tpe')
    paths=sorted(a.output.glob('trial_*.json'))
    hashes={f.name:sha256(f.read_bytes()).hexdigest() for f in paths}
    resumed=run_campaign(request,a.dataset,a.output,mode='tpe')
    assert hashes=={f.name:sha256(f.read_bytes()).hexdigest() for f in sorted(a.output.glob('trial_*.json'))}
    records=[read_trial(f) for f in paths]
    assert len(records)==5 and result['completed_trials']==resumed['completed_trials']==5
    assert records[0]['result']['result']=='SIMULATED'
    assert any(sum(r['proposal'][k]!=records[0]['proposal'][k] for k in r['proposal'])>=2 for r in records[1:])
    assert before==sha256(CONFIG_PATH.read_bytes()).hexdigest()
    evidence={'acceptance':'PASS','deployment':deployment_diagnostics(),'request':request.model_dump(mode='json'),
        'status':result,'resume_status':resumed,'sha256':hashes,'trading_yaml_sha256':before,
        'trials':[{'number':r['number'],'proposal':r['proposal'],'configuration_hash':r['configuration_hash'],
            'result':r['result']['result'],'net_pnl':r['result'].get('net_pnl'),
            'events':len(r['result'].get('events',[])),'blockers':len(r['result'].get('blockers',[])),
            'closed_trades':len(r['result'].get('closed_trades',[]))} for r in records]}
    (a.output/'ACCEPTANCE.json').write_text(json.dumps(evidence,sort_keys=True,indent=2))
    print(json.dumps(evidence,indent=2),flush=True)


if __name__=='__main__':main()
