"""Installed verifier smoke: real baseline roundtrip, no fabricated finding."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import yaml

from app.config.trade_parameters import CONFIG_PATH
from traders_ml.parameter_sweep.generated_search import run_campaign
from traders_ml.parameter_sweep.finding_verifier import export_configuration,load_export,flatten
from traders_ml.parameter_sweep.result_search import SearchRequest,deployment_diagnostics,fingerprint
from traders_ml.parameter_sweep.search_history import HistoryProvider
from traders_ml.parameter_sweep.frozen_funnel import SEARCHABLE_PARAMETERS
from traders_ml.parameter_sweep.chronological_search import simulate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    before=sha256(CONFIG_PATH.read_bytes()).hexdigest()
    request=SearchRequest.model_validate_json(Path('docs/audits/BLOCK_02_REQUEST.json').read_text())
    request=request.model_copy(update={'max_trials':1,'max_wall_time':600.0})
    result=run_campaign(request,a.dataset,a.output)
    assert not result['found'] and not json.loads((a.output/'SUCCESSFUL_CONFIGS.json').read_text())
    _,rows=HistoryProvider.load(a.dataset)
    frozen=next(r['frozen'] for r in rows if r['kind']=='PERSISTED_BOUNDARY')
    exported=a.output/'ROUNDTRIP_BASELINE_NOT_A_FINDING.yaml'
    exported.write_text(yaml.safe_dump(export_configuration(frozen,{})))
    loaded=load_export(exported,frozen)
    flat=flatten(loaded.parameters.model_dump(mode='json'))
    replay=simulate(a.dataset,{k:flat[k] for k in SEARCHABLE_PARAMETERS},request.initial_capital)
    first=json.loads((a.output/'trial_000000.json').read_text())['result']
    assert replay==first and loaded.resolved_config_hash==first['configuration_fingerprint']
    assert sha256(CONFIG_PATH.read_bytes()).hexdigest()==before
    evidence={'acceptance':'PASS_ENGINEERING_NO_HISTORICAL_FINDING','deployment':deployment_diagnostics(),
        'result':result,'roundtrip_hash':loaded.resolved_config_hash,'replay_fingerprint':fingerprint(replay),
        'trading_yaml_sha256':before,'real_closed_trades':len(replay['closed_trades']),
        'real_net_pnl':replay['net_pnl'],'positive_export_tests':'SEE_FRESH_PYTEST_EVIDENCE_SYNTHETIC_ONLY'}
    (a.output/'ACCEPTANCE.json').write_text(json.dumps(evidence,sort_keys=True,indent=2))
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':main()
