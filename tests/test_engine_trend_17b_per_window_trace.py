import csv, json, re
from pathlib import Path

ROOT=Path("reports/engine_trend/per_window_trace")
REPORT=Path("reports/engine_trend/engine_trend_17b_per_window_market_evidence_trace_expansion_report.md")

def read(name): return json.loads((ROOT/name).read_text(encoding="utf-8"))

def test_behavior_lock_contract():
    lock=read("ENGINE_TREND_17B_BEHAVIOR_LOCK.json")
    assert lock["window_count"] >= 60
    assert lock["behavior_changed"] is False
    assert lock["safety_violations"] == 0
    assert lock["market_regime_counts"] == {"UNKNOWN":60}
    assert lock["confidence_counts"] == {"0.3":60}

def test_summary_artifacts_exist_and_parse():
    matrix=read("ENGINE_TREND_17B_TRACE_COVERAGE_MATRIX.json")
    assert matrix["window_count"] >= 60 and len(matrix["rows"]) >= 60
    with (ROOT/"ENGINE_TREND_17B_TRACE_COVERAGE_MATRIX.csv").open(encoding="utf-8") as h: assert len(list(csv.DictReader(h))) >= 60
    missing=read("ENGINE_TREND_17B_MISSING_TRACE_FIELDS.json")
    assert missing["whether_behavior_change_is_needed"] is False
    assert (ROOT/"ENGINE_TREND_17B_PER_WINDOW_INDEX.md").exists()
    assert (ROOT/"ENGINE_TREND_17B_EVIDENCE_VISIBILITY_SUMMARY.md").exists()
    assert REPORT.exists()

def test_manifest_contract():
    manifest=read("ENGINE_TREND_17B_ARTIFACT_MANIFEST.json")
    assert manifest["window_count"] >= 60
    assert manifest["core_behavior_changed"] is False
    assert manifest["adapter_changed"] is False and manifest["db_cli_changed"] is False
    assert manifest["runtime_trading_allowed"] is False
    assert manifest["trading_claims_allowed"] is False
    assert len(manifest["sha256_checksums"]) >= 127

def test_per_window_trace_contracts():
    json_files=list((ROOT/"json").glob("*_trace.json")); md_files=list((ROOT/"markdown").glob("*_trace.md"))
    assert len(json_files) >= 60 and len(md_files) >= 60
    required={"stage","source_stage","window","final_result","nison_candle_trace","altunina_trend_trace","schwager_range_trace","book_evidence_matrix_trace","composer_trace","human_readable_explanation","trace_completeness"}
    headings=("## 1. Nison candle context","## 2. Altunina trend context","## 3. Schwager range context","## 4. BookEvidenceMatrix","## 5. Composer decision")
    for path in json_files:
        value=json.loads(path.read_text(encoding="utf-8")); assert required <= value.keys()
        final=value["final_result"]
        assert final["market_regime"]=="UNKNOWN" and final["confidence"]==0.3
        assert final["trade_signal"]=="NOT_EVALUATED"
        assert final["safe_for_runtime_trading"] is False and final["live_trading_connected"] is False
    for path in md_files:
        body=path.read_text(encoding="utf-8"); assert all(x in body for x in headings)

def test_artifacts_contain_no_credentials():
    patterns=re.compile(r"postgresql(?:\+psycopg2?)?://|DATABASE_URL\s*=|POSTGRES_PASSWORD\s*=|password\s*[:=]",re.I)
    for path in ROOT.rglob("*"):
        if path.is_file(): assert not patterns.search(path.read_text(encoding="utf-8")), path
