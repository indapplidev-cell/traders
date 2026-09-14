from pathlib import Path
import json
import pytest
from traders_ml.parameter_sweep.search_optimizer import SearchOptimizer,objective


def create(path,mode="exhaustive",seed=11):
    return SearchOptimizer(path,identity={"test":"synthetic"},domains={"a":[0,1],"b":[0,1]},
                           baseline={"a":0,"b":0},seed=seed,mode=mode)


def evaluate(p):
    win=p=={"a":1,"b":1}
    return {"result":"SIMULATED","blockers":[],"net_pnl":1 if win else 0,
            "closed_trades":[{"net_pnl":1}] if win else []}


def run(search,n=20,evaluator=evaluate,validator=lambda p:p):
    return search.run(evaluator,validator,max_trials=n,max_wall_time=60,storage_budget_bytes=4000000)


def test_exhaustive_joint_success_and_resume(tmp_path):
    calls=[]
    def evaluator(p): calls.append(p);return evaluate(p)
    assert run(create(tmp_path),2,evaluator)["completed_trials"]==2
    result=run(create(tmp_path),20,evaluator)
    assert result["outcome"]=="SEARCH_SPACE_EXHAUSTED" and len(calls)==4
    assert {tuple(sorted(p.items())) for p in calls}=={(("a",a),("b",b)) for a in (0,1) for b in (0,1)}
    assert sum(objective(evaluate(p))>1 for p in calls)==1


def test_tpe_resume_matches_uninterrupted(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b'
    run(create(a,"tpe"),9)
    run(create(b,"tpe"),4);run(create(b,"tpe"),9)
    read=lambda p:[json.loads(f.read_text())["proposal"] for f in sorted(p.glob('trial_*.json'))]
    assert read(a)==read(b)


def test_invalid_not_evaluated_and_incompatible_resume(tmp_path):
    calls=[]
    def validator(p):
        if p['a']:raise ValueError('invalid')
        return p
    run(create(tmp_path),20,lambda p:(calls.append(p) or evaluate(p)),validator)
    assert len(calls)==2
    with pytest.raises(ValueError,match="INCOMPATIBLE"):
        run(create(tmp_path,seed=12))


def test_invalid_replay_cannot_score_positive():
    assert objective({"result":"BLOCKED_DATA","net_pnl":100,"closed_trades":[{"net_pnl":100}]})<0


def test_interrupted_trial_remains_resumable(tmp_path):
    interrupted=lambda p:{"result":"BLOCKED_DATA","blockers":[{"reason":"TRIAL_INTERRUPTED_BY_BUDGET_OR_CANCEL"}]}
    assert run(create(tmp_path),1,interrupted)["completed_trials"]==0
    assert not list(tmp_path.glob('trial_*.json'))
    assert run(create(tmp_path),1)["completed_trials"]==1


def test_crash_after_atomic_record_recovers_without_simulation(tmp_path,monkeypatch):
    import optuna
    original=optuna.study.Study.tell
    def crash(*a,**kw):raise RuntimeError('crash before tell')
    monkeypatch.setattr(optuna.study.Study,'tell',crash)
    with pytest.raises(RuntimeError,match='crash'):
        run(create(tmp_path),1)
    monkeypatch.setattr(optuna.study.Study,'tell',original)
    def forbidden(p):raise AssertionError('must recover persisted result')
    assert run(create(tmp_path),1,forbidden)["completed_trials"]==1


def test_waiting_last_grid_trial_survives_restart(tmp_path,monkeypatch):
    import optuna
    run(create(tmp_path),3)
    original=optuna.study.Study.ask
    def crash(*a,**kw):raise RuntimeError('crash after enqueue')
    monkeypatch.setattr(optuna.study.Study,'ask',crash)
    with pytest.raises(RuntimeError,match='enqueue'):
        run(create(tmp_path),4)
    monkeypatch.setattr(optuna.study.Study,'ask',original)
    assert run(create(tmp_path),4)["completed_trials"]==4
