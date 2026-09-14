import json
from pathlib import Path

import pytest

from traders_ml.parameter_sweep.result_search import (
    ClosedTradeProof, ENGINE_VERSION, ExecutionState as S, ResultSearchService,
    SearchOutcome as O, SearchRequest, fingerprint,
)


def values():
    return dict(symbols=["BTCUSDT"], scope="SINGLE_SYMBOL", start="2026-09-10T00:00:00Z",
                end="2026-09-11T00:00:00Z", data_cutoff="2026-09-12T00:00:00Z",
                initial_capital=100, baseline_hash="a" * 64, seed=7, max_trials=5,
                max_wall_time=60, artifact_budget_bytes=100000, storage_budget_bytes=200000,
                data_mode="HISTORICAL_VERIFIED")


def setup_run(tmp_path):
    service = ResultSearchService()
    return service, service.prepare(SearchRequest(**values()), tmp_path, "b" * 64)


def proof(**changes):
    data = dict(trade_id="test-only", config_hash=fingerprint({"full": "config"}),
                dataset_hash="b" * 64, engine=ENGINE_VERSION, entry_valid=True,
                closed=True, exit_reason="TARGET", gross_pnl=2, costs=1, net_pnl=1,
                causal=True, replay_verified=True)
    return ClosedTradeProof(**(data | changes))


@pytest.mark.parametrize("changes", [dict(closed=False), dict(exit_reason="PATH_END"),
    dict(costs=3, net_pnl=-1), dict(net_pnl=4), dict(causal=False),
    dict(replay_verified=False), dict(entry_valid=False)])
def test_nonqualifying_trade_never_found(tmp_path, changes):
    service, run = setup_run(tmp_path)
    service.transition(run, S.RUNNING)
    service.transition(run, S.VERIFYING)
    with pytest.raises(ValueError):
        service.persist_verified_proof(run, proof(**changes), {"full": "config"})
    assert json.loads((run / "STATUS.json").read_text())["outcome"] is None


def test_one_trade_sufficient_only_after_durable_verification(tmp_path):
    service, run = setup_run(tmp_path)
    service.transition(run, S.RUNNING)
    with pytest.raises(ValueError):
        service.transition(run, S.TERMINAL, outcome=O.FOUND)
    service.transition(run, S.VERIFYING)
    with pytest.raises(FileNotFoundError):
        service.transition(run, S.TERMINAL, outcome=O.FOUND)
    service.persist_verified_proof(run, proof(), {"full": "config"})
    ResultSearchService().transition(run, S.TERMINAL, outcome=O.FOUND)
    status = json.loads((run / "STATUS.json").read_text())
    assert status["outcome"] == "FOUND"
    assert status["independent_validation"] == "NOT_EVALUATED"


@pytest.mark.parametrize("outcome", [o for o in O if o != O.FOUND])
def test_terminal_outcomes_do_not_invent_finding(tmp_path, outcome):
    service, run = setup_run(tmp_path)
    service.transition(run, S.TERMINAL, outcome=outcome)
    assert not (run / "REPLAY_PROOF.json").exists()
    with pytest.raises(ValueError):
        service.transition(run, S.RUNNING)


@pytest.mark.parametrize("key", ["contract", "request", "dataset", "baseline", "registry", "engine"])
def test_resume_rejects_every_incompatible_identity(tmp_path, key):
    service, run = setup_run(tmp_path)
    manifest = json.loads((run / "SEARCH_MANIFEST.json").read_text())
    manifest["identity"][key] = "different"
    (run / "SEARCH_MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="INCOMPATIBLE_RESUME"):
        service.prepare(SearchRequest(**values()), tmp_path, "b" * 64, resume=run)


def test_cli_gui_contract_parity(tmp_path, capsys):
    from traders_ml.parameter_sweep.cli import main
    from traders_ml.parameter_sweep.controller import ParameterSweepController
    request = tmp_path / "request.json"
    request.write_text(json.dumps(values()))
    main(["--result-search-request", str(request), "--output-root", str(tmp_path),
          "--result-search-dataset-hash", "b" * 64])
    cli_run = Path(json.loads(capsys.readouterr().out)["run"])
    gui_run = ParameterSweepController.prepare_result_search(values(), tmp_path, "b" * 64)
    left = json.loads((cli_run / "SEARCH_MANIFEST.json").read_text())
    right = json.loads((gui_run / "SEARCH_MANIFEST.json").read_text())
    assert left["identity"] == right["identity"]
    assert left["request"] == right["request"]


@pytest.mark.parametrize("changes", [dict(max_trials=0), dict(max_wall_time=-1),
    dict(scope="SINGLE_SYMBOL", symbols=["BTCUSDT", "ETHUSDT"]), dict(initial_capital=float("nan")),
    dict(start="2026-09-10T00:00:00"), dict(end="2026-09-13T00:00:00Z"),
    dict(symbols=[]), dict(parameters={"x": []})])
def test_invalid_request_rejected(changes):
    with pytest.raises(ValueError):
        SearchRequest(**(values() | changes))


def test_saved_proof_tampering_and_failed_save_do_not_publish(tmp_path, monkeypatch):
    service, run = setup_run(tmp_path)
    service.transition(run, S.RUNNING)
    service.transition(run, S.VERIFYING)
    service.persist_verified_proof(run, proof(), {"full": "config"})
    (run / "VERIFIED_CONFIG.json").write_text('{}')
    with pytest.raises(ValueError, match="CONFIG_IDENTITY"):
        service.transition(run, S.TERMINAL, outcome=O.FOUND)
    def fail(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(service, "_write", fail)
    with pytest.raises(OSError):
        service.persist_verified_proof(run, proof(), {"full": "config"})
    assert json.loads((run / "STATUS.json").read_text())["outcome"] is None
