"""Read-only installed chronological simulator acceptance on frozen history."""
import argparse
import json
from pathlib import Path
from hashlib import sha256
from collections import Counter

from app.config.trade_parameters import CONFIG_PATH
from traders_ml.parameter_sweep.chronological_search import simulate
from traders_ml.parameter_sweep.result_search import deployment_diagnostics
from traders_ml.parameter_sweep.search_history import HistoryProvider


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    before=sha256(CONFIG_PATH.read_bytes()).hexdigest()
    manifest,rows=HistoryProvider.load(a.dataset)
    old={(r["symbol"],r["closed_until_ms"]):r for r in rows if r["kind"]=="PERSISTED_BOUNDARY"}
    results=[]
    for overrides in ({},{"signal.strategy_minimum_score":100},{"geometry.stop_max_bps":60}):
        result=simulate(a.dataset,overrides,100)
        path=a.output/f"TRIAL_{len(results)}.json"
        path.write_text(json.dumps(result,sort_keys=True,indent=2))
        parity=[]
        for event in result["events"]:
            source=old[(event["symbol"],event["boundary"])]
            reason=(source.get("geometry") or {}).get("rejection_reason") or source["paper_status"]
            parity.append(event["status"]==source["paper_status"] and event["reason"]==reason)
        results.append({"overrides":overrides,"result":result["result"],"quality":result["quality"],
            "events":len(result["events"]),"baseline_parity":dict(Counter(parity)),
            "rejections":result["rejections"],"blocker_counts":dict(Counter(b["reason"] for b in result["blockers"])),
            "closed_trades":len(result["closed_trades"]),"net_pnl":result["net_pnl"],
            "sha256":sha256(path.read_bytes()).hexdigest(),"configuration_fingerprint":result["configuration_fingerprint"]})
        print(json.dumps(results[-1]),flush=True)
    assert results[0]["baseline_parity"]=={True:480}
    assert results[0]["blocker_counts"]=={}
    assert results[1]["rejections"]!=results[0]["rejections"]
    assert before==sha256(CONFIG_PATH.read_bytes()).hexdigest()
    evidence={"deployment":deployment_diagnostics(),"dataset_fingerprint":manifest["fingerprint"],
        "trading_yaml_sha256":before,"trials":results,"acceptance":"REAL_CHRONOLOGICAL_FUNNEL_PASS",
        "profitable_historical_trade_found":False,"no_production_writes":True}
    (a.output/"ACCEPTANCE.json").write_text(json.dumps(evidence,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
