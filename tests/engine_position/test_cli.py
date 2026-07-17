import json
from pathlib import Path
import subprocess
import sys
from tests.engine_position.conftest import make_contract

ROOT=Path(__file__).resolve().parents[2]
CLI=ROOT/"scripts"/"engine_position_dry_run.py"
def write_input(tmp_path,mode="DRY_RUN",mutate=None):
 i,a=make_contract(mode=mode); d={"execution_intent":i.to_dict(),"execution_acknowledgement":a.to_dict()}
 if mutate: mutate(d)
 p=tmp_path/"input.json"; p.write_text(json.dumps(d),encoding="utf-8"); return p
def run(path,mode,*extra): return subprocess.run([sys.executable,str(CLI),str(path),"--mode",mode,*extra],cwd=ROOT,text=True,capture_output=True)
def parsed(r): return json.loads(r.stdout)
def test_59_cli_paper(tmp_path):
 r=run(write_input(tmp_path,"PAPER"),"PAPER"); assert r.returncode==0 and parsed(r)["position"]["mode"]=="PAPER"
def test_60_cli_dry_run(tmp_path):
 r=run(write_input(tmp_path),"DRY_RUN","--synthetic-local-fill"); assert r.returncode==0 and parsed(r)["position"]["status"]=="OPEN"
def test_61_cli_live_is_nonzero_and_blocked(tmp_path):
 r=run(tmp_path/"absent.json","LIVE"); assert r.returncode!=0 and parsed(r)["reason_codes"]==["LIVE_POSITION_MANAGEMENT_DISABLED"]
def test_62_cli_invalid_mode_is_safe_json(tmp_path):
 r=run(tmp_path/"absent.json","INVALID"); assert r.returncode!=0 and parsed(r)["reason_codes"]==["MODE_MISMATCH"]
def test_63_cli_invalid_json(tmp_path):
 p=tmp_path/"x"; p.write_text("{",encoding="utf-8"); r=run(p,"DRY_RUN"); assert r.returncode!=0 and parsed(r)["ok"] is False
def test_64_cli_missing_file(tmp_path):
 r=run(tmp_path/"missing","DRY_RUN"); assert r.returncode!=0 and parsed(r)["error_type"]=="FileNotFoundError"
def test_65_cli_missing_field(tmp_path):
 p=tmp_path/"x"; p.write_text("{}",encoding="utf-8"); r=run(p,"DRY_RUN"); assert r.returncode!=0 and parsed(r)["error_type"]=="KeyError"
def test_66_cli_non_finite_value(tmp_path):
 def mutate(d): d["execution_intent"]["reference_price"]="NaN"
 r=run(write_input(tmp_path,mutate=mutate),"DRY_RUN"); assert r.returncode!=0 and "INVALID_ENTRY_PRICE" in parsed(r)["reason_codes"]
def test_67_cli_stdout_contains_only_one_json_document(tmp_path):
 r=run(write_input(tmp_path),"DRY_RUN"); assert len(r.stdout.splitlines())==1 and r.stderr==""
def test_68_cli_creates_no_reports_or_artifacts(tmp_path):
 before={p.name for p in tmp_path.iterdir()}; run(next(tmp_path.iterdir()) if before else write_input(tmp_path),"DRY_RUN"); after={p.name for p in tmp_path.iterdir()}; assert before==after or after=={"input.json"}
