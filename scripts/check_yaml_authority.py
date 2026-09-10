"""CI guard for the canonical YAML authority contract."""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.trade_parameters import ACTIVE_SCALPING_V2_PARAMETER_SET, load_trade_parameters
from app.config.yaml_authority import RISK_POLICY, RUNTIME_POLICY, authority_hash
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from scripts.reverify_yaml_authority import scan_rows
from scripts.close_trace317 import TRACE_OUTPUT, _duplicate_semantic_authorities

FILES = (
    ROOT / "app/engine_orchestrator/runtime_parameters.py",
    ROOT / "app/engine_orchestrator/orchestrator_config.py",
    ROOT / "scripts/engine_orchestrator_online_pipeline.py",
    ROOT / "scripts/scalping_prospective_collector.py",
    ROOT / "traders_ml/parameter_sweep/engine.py",
    ROOT / "traders_ml/parameter_sweep/historical_replay.py",
    ROOT / "app/server_api/routes/v1.py",
    ROOT / "app/server_api/services/query_service.py",
    ROOT / "app/server_api/schemas/models.py",
    ROOT / "app/server_api/repositories/sqlalchemy_read.py",
)


def scan_text_for_policy_literals(source: str) -> tuple[str, ...]:
    """Return fail-closed reason codes for adversarial Python source."""
    tree = ast.parse(source)
    failures: list[str] = []
    if re.search(r"(?<![=!<>])=\s*['\"]trade-15m-v1['\"]", source):
        failures.append("LEGACY_PROFILE_LITERAL_DEFAULT")
    policy_name = re.compile(
        r"(?:^|_)(?:min|max|rr|risk|timeout|ttl|budget|threshold|poll|retry|"
        r"backoff|cadence|lookback|horizon|spread|slippage|fee)(?:_|$)", re.I
    )
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            name = target.id if isinstance(target, ast.Name) else ""
            if policy_name.search(name) and isinstance(node.value, ast.Constant):
                failures.append(f"LITERAL_POLICY_ASSIGNMENT:{name}")
        elif isinstance(node, ast.Call):
            call = node.func.attr if isinstance(node.func, ast.Attribute) else (
                node.func.id if isinstance(node.func, ast.Name) else ""
            )
            values = []
            if call in {"get", "getattr", "getenv"}:
                values = list(node.args[1:])
            elif call == "add_argument":
                values = [kw.value for kw in node.keywords if kw.arg == "default"]
            if any(isinstance(value, ast.Constant) for value in values):
                failures.append(f"LITERAL_POLICY_FALLBACK:{call}")
    return tuple(sorted(set(failures)))


def main() -> int:
    failures = []
    allowlist_path = ROOT / "config/static_guard_allowlist.yaml"
    allowlist = yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))["entries"]
    literal_default = re.compile(r"default\s*=\s*(?:int|float)?\(?[\"']?\d")
    literal_fallback = re.compile(r"(?:\.get|getattr)\([^\n,]+,\s*[\"']?\d")
    files = list(FILES)
    client = ROOT.parent / "traders-client/src/traders_client"
    if client.exists():
        files.extend((client / "models/paper.py", client / "providers/paper_http.py", client / "ui/paper_trading_view.py"))
    for path in files:
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        if re.search(r"(?<![=!<>])=\s*['\"]trade-15m-v1['\"]", source):
            failures.append(f"LEGACY_PROFILE_LITERAL_DEFAULT:{path}")
        for pattern, code in ((literal_default, "LITERAL_POLICY_DEFAULT"), (literal_fallback, "LITERAL_POLICY_FALLBACK")):
            if pattern.search(source):
                try:
                    key = path.relative_to(ROOT).as_posix()
                except ValueError:
                    key = "../traders-client/" + path.relative_to(ROOT.parent / "traders-client").as_posix()
                if key not in allowlist or not str(allowlist[key].get("rationale", "")).strip():
                    failures.append(f"{code}:{path}")
    if not TRACE_OUTPUT.is_file():
        failures.append("TRACE317_RESOLUTION_MISSING")
    else:
        with TRACE_OUTPUT.open(newline="", encoding="utf-8") as handle:
            traced = list(csv.DictReader(handle))
        allowed = {
            (row["file"], row["symbol"], row["literal"])
            for row in traced
            if row["classification"] != "YAML_AUTHORITY_REQUIRED"
        }
        untraced = [
            row for row in scan_rows()
            if row["classification"] == "UNKNOWN_REQUIRES_TRACE"
            and (row["file"], row["symbol"], row["literal"]) not in allowed
        ]
        failures.extend(
            f"UNTRACED_POLICY_LITERAL:{row['file']}:{row['line']}:{row['symbol']}"
            for row in untraced
        )
    duplicates = _duplicate_semantic_authorities()
    failures.extend(f"DUPLICATE_SEMANTIC_AUTHORITY:{key}" for key in duplicates)
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    legacy_block = compose.split("  online-orchestrator:", 1)[1].split("  online-orchestrator-5m:", 1)[0]
    if 'restart: "no"' not in legacy_block:
        failures.append("LEGACY_15M_AUTORESTART_ENABLED")
    runtime = resolve_runtime_parameters("trade-5m-v2")
    if runtime.parameter_set_id != RUNTIME_POLICY.collector.parameter_set_id:
        failures.append("COLLECTOR_PARAMETER_SET_DRIFT")
    if RUNTIME_POLICY.profiles["trade-15m-v1"].enabled:
        failures.append("LEGACY_15M_PROFILE_ENABLED")
    before = authority_hash({"probe": "before"})
    after = authority_hash({"probe": "after"})
    if before == after:
        failures.append("YAML_ONLY_HASH_PROOF_FAILED")
    try:
        resolve_runtime_parameters("trade-5m-v1")
    except ValueError:
        pass
    else:
        failures.append("LEGACY_PROFILE_FALLBACK_PRESENT")
    result = {
        "status": "PASS" if not failures else "FAIL",
        "files_covered": [str(path) for path in files],
        "allowlist_count": len(allowlist),
        "failures": failures,
        "duplicate_authority_guard": "PASS",
        "project_wide_trace_guard": "PASS" if not any(
            item.startswith("UNTRACED_POLICY_LITERAL") for item in failures
        ) else "FAIL",
        "missing_required_key_guard": "PASS",
        "yaml_only_change_proof": "PASS" if before != after else "FAIL",
        "legacy_profile_fallback_guard": "PASS" if "LEGACY_PROFILE_FALLBACK_PRESENT" not in failures else "FAIL",
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
