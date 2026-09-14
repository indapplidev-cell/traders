"""Fresh-process, read-only block 02 acceptance. Large outputs stay local."""
from pathlib import Path
import argparse
import json
from datetime import datetime
from hashlib import sha256
from sqlalchemy import text

from app.config.trade_parameters import CONFIG_PATH
from traders_ml.parameter_sweep.result_search import SearchRequest, deployment_diagnostics
from traders_ml.parameter_sweep.search_history import HistoryProvider
from traders_ml.parameter_sweep.history_applicability import assess_dataset
from traders_ml.parameter_sweep.engine import ReadOnlyResearchDatabase, resolve_database_binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    request = SearchRequest.model_validate_json(Path("artifacts/result_search_refactor/block02/request_global.json").read_text())
    before = sha256(CONFIG_PATH.read_bytes()).hexdigest()
    manifest = HistoryProvider().freeze(request, args.output / "dataset",
        statistics_source=Path("reports/calibration/scalping-v2-probability-set2"),
        parameter_set_id="scalping-v2-set-2")
    assert manifest["missing_inputs"] == []
    assert HistoryProvider.load(args.output / "dataset")[0]["fingerprint"] == manifest["fingerprint"]
    combinations = json.loads(Path("artifacts/result_search_applicability_01/combinations.json").read_text())
    assessment = assess_dataset(args.output / "dataset", combinations)
    (args.output / "ASSESSMENT.json").write_text(json.dumps(assessment, sort_keys=True))
    independent_request = request.model_copy(update={"symbols": ("BTCUSDT",), "scope": "SINGLE_SYMBOL",
        "end": datetime.fromisoformat("2026-09-13T20:00:00+00:00")})
    evaluation = (int(datetime.fromisoformat("2026-09-13T21:00:00+00:00").timestamp()*1000),
                  int(datetime.fromisoformat("2026-09-13T23:00:00+00:00").timestamp()*1000))
    independent = HistoryProvider().freeze(independent_request, args.output / "independent", independent_interval=evaluation)
    assert not independent["missing_inputs"]
    split_counts = {name: len(HistoryProvider.partition(args.output / "independent", name)) for name in
                    ("warmup", "search", "exit_tail", "independent_evaluation", "independent_exit_tail")}
    assert all(split_counts.values())
    _, search = HistoryProvider.search_view(args.output / "independent")
    assert all((r["close_time_ms"] if r["kind"] == "CANDLE" else r["closed_until_ms"]) <
               independent["intervals"]["search_end_ms"] for r in search)
    database = ReadOnlyResearchDatabase(resolve_database_binding())
    try:
        with database.connection() as connection:
            sql = {"read_only": connection.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one(),
                   "alembic": connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                   "btc_paper_positions": connection.execute(text("SELECT count(*) FROM paper_positions WHERE symbol='BTCUSDT'")).scalar_one()}
    finally:
        database.dispose()
    assert sql["read_only"] == "on" and sql["btc_paper_positions"] == 0
    statistics = json.loads((args.output / "dataset/STATISTICS.json").read_text())
    after = sha256(CONFIG_PATH.read_bytes()).hexdigest()
    assert before == after == request.baseline_hash
    result = {"deployment": deployment_diagnostics(), "dataset": manifest, "sql": sql,
              "independent": independent, "partition_counts": split_counts,
              "statistics": {k: v for k, v in statistics.items() if k not in ("outcomes", "source_files")},
              "assessment_sha256": sha256((args.output / "ASSESSMENT.json").read_bytes()).hexdigest(),
              "combinations": [{k:v for k,v in r.items() if k != "details"} for r in assessment["combinations"]],
              "boundary_coverage": assessment["boundary_coverage"], "dataset_hard_blockers": assessment["dataset_hard_blockers"],
              "trading_yaml_sha256": after, "verdict": "HISTORY_ACCEPTANCE_PASS", "full_trade_simulation": False}
    (args.output / "ACCEPTANCE.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({"output": str(args.output), "verdict": result["verdict"], "deployment": result["deployment"]}))


if __name__ == "__main__":
    main()
