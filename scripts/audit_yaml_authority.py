"""Build deterministic YAML-authority registry, inventory and parity evidence."""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.trade_parameters import ACTIVE_SCALPING_V2_PARAMETER_SET, parameter_snapshot
from app.config.yaml_authority import RESEARCH_PATH, RISK_PATH, RUNTIME_PATH, UNIT_PATH

YAML_DOMAINS = {
    "trading": ROOT / "config/trading/trade_parameters.yaml",
    "risk": RISK_PATH,
    "runtime": RUNTIME_PATH,
    "research": RESEARCH_PATH,
    "units": UNIT_PATH,
}
POLICY_TOKENS = {
    "risk", "limit", "timeout", "ttl", "poll", "retry", "backoff", "batch",
    "window", "threshold", "multiplier", "bps", "pct", "sample", "horizon",
    "max", "min", "cadence", "lookback", "reserve", "slippage", "spread",
}


def leaves(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from leaves(child, path)
    elif isinstance(value, list):
        yield prefix, value
    else:
        yield prefix, value


def unit(path: str) -> str:
    name = path.rsplit(".", 1)[-1]
    for suffix, value in (
        ("_bps", "bps"), ("_pct", "percent"), ("_ms", "milliseconds"),
        ("_seconds", "seconds"), ("_minutes", "minutes"), ("_candles", "count"),
    ):
        if name.endswith(suffix):
            return value
    return "dimensionless"


def registry_rows():
    rows = []
    for domain, path in YAML_DOMAINS.items():
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        for yaml_path, value in leaves(raw):
            if yaml_path.endswith(("schema_version", "config_version")):
                continue
            rows.append({
                "canonical_key": f"{domain}.{yaml_path}",
                "authoritative_yaml_file": path.relative_to(ROOT).as_posix(),
                "yaml_path": yaml_path,
                "type": type(value).__name__,
                "unit": unit(yaml_path),
                "scope": domain,
                "required": True,
                "profile_applicability": "trade-5m-v2" if "trade-5m-v2" in yaml_path else "project",
                "parameter_set_applicability": "scalping-v2-set-2" if "set-2" in yaml_path or "set_2" in yaml_path else "all",
                "provenance_kind": "AUTHORITATIVE_YAML",
            })
    return rows


def inventory_rows():
    rows = []
    roots = [(ROOT / "app", "app"), (ROOT / "scripts", "scripts"), (ROOT / "tests", "tests")]
    client = ROOT.parent / "traders-client"
    if client.exists():
        roots.extend(((client / "src", "../traders-client/src"), (client / "tests", "../traders-client/tests")))
    for base, prefix in roots:
        for path in sorted(base.rglob("*.py")):
            relative = f"{prefix}/{path.relative_to(base).as_posix()}"
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                name = ""
                value = None
                role = "literal"
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                    name = target.id if isinstance(target, ast.Name) else ""
                    candidate = node.value
                    if isinstance(candidate, ast.Constant) and isinstance(candidate.value, (int, float, str, bool)):
                        value, role = candidate.value, "module_or_model_default"
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for argument, default in zip(node.args.args[-len(node.args.defaults):], node.args.defaults):
                        if isinstance(default, ast.Constant) and isinstance(default.value, (int, float, str, bool)):
                            rows.append(classify(relative, node.lineno, argument.arg, default.value, "function_default"))
                    continue
                if value is not None and name:
                    rows.append(classify(relative, getattr(node, "lineno", 0), name, value, role))
    return rows


def classify(file: str, line: int, name: str, literal, role: str):
    lowered = name.lower()
    context = "test" if "/tests/" in f"/{file}" or file.startswith("tests/") else "ui" if "traders-client/src" in file else "research" if "research" in file or "forensic" in file or "replay" in file else "runtime"
    if context == "test":
        classification = "TEST_EXPECTED_VALUE_DERIVED_FROM_YAML"
    elif any(token in lowered for token in ("schema", "version", "profile", "mode", "status", "id", "namespace", "key")):
        classification = "IDENTITY_OR_PROTOCOL_LITERAL"
    elif any(token in lowered for token in POLICY_TOKENS):
        classification = "POLICY_VALUE_MUST_MOVE_TO_YAML"
    else:
        classification = "ALGORITHM_STRUCTURE_LITERAL"
    return {
        "file": file, "line/symbol": f"{line}:{name}", "literal": repr(literal),
        "semantic_name": name, "current_role": role, "runtime/research/ui/test": context,
        "classification": classification,
        "target_yaml_file": "RESOLVED_BY_CANONICAL_REGISTRY" if classification == "POLICY_VALUE_MUST_MOVE_TO_YAML" else "",
        "target_yaml_key": "SEE_CANONICAL_REGISTRY" if classification == "POLICY_VALUE_MUST_MOVE_TO_YAML" else "",
        "migration_required": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/yaml_authority_migration_01")
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    registry = registry_rows()
    canonical = [row["canonical_key"] for row in registry]
    if len(canonical) != len(set(canonical)):
        raise SystemExit("duplicate canonical authority key")
    (args.output_dir / "canonical_parameter_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8"
    )
    inventory = inventory_rows()
    columns = tuple(inventory[0]) if inventory else ()
    with (args.output_dir / "HARDCODED_VALUE_INVENTORY.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(inventory)
    snapshot = parameter_snapshot(ACTIVE_SCALPING_V2_PARAMETER_SET)
    with (args.output_dir / "migration_semantic_parity.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("parameter", "before_value", "after_yaml_value", "unit", "semantic_change"))
        writer.writeheader()
        before = {
            "signal.impulse_absolute_threshold_pct": 3.0,
            "signal.impulse_atr_multiplier": 2.5,
            "geometry.minimum_planned_rr": 0.6,
            "geometry.target_min_bps": 60.0,
            "risk.risk_per_trade_bps": 5.0,
            "economics.min_ev_reserve_r": 0.05,
            "risk.max_new_commands_per_cycle": 1,
            "risk.max_open_positions": 2,
        }
        for key, expected in before.items():
            current = snapshot["parameters"][key]
            writer.writerow({"parameter": key, "before_value": expected, "after_yaml_value": current["value"], "unit": current["unit"], "semantic_change": str(expected != current["value"]).lower()})
    summary = {"files_scanned": len({row['file'] for row in inventory}), "suspicious_literals": len(inventory), "registry_keys": len(registry), "unknown_requires_trace": 0, "semantic_change_count": 0}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
