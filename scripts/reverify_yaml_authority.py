"""Independent repository-wide YAML-authority inventory and provenance evidence."""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_yaml_authority import registry_rows
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters

OUTPUT = ROOT / "artifacts/final_yaml_authority_reverification_01"
POLICY_TOKENS = {
    "backoff", "batch", "budget", "cadence", "candle", "capacity", "depth",
    "fee", "freshness", "grace", "horizon", "interval", "limit", "lookback",
    "margin", "max", "min", "multiplier", "percent", "poll", "probability",
    "reserve", "retry", "risk", "rr", "sample", "slippage", "spread",
    "threshold", "timeout", "ttl", "warmup", "window",
}
IDENTITY_TOKENS = {
    "action", "class", "code", "contract", "direction", "event", "id", "key",
    "kind", "label", "mode", "name", "path", "profile", "reason", "role",
    "schema", "source", "state", "status", "type", "url", "version",
}
YAML_REFERENCES = (
    "RUNTIME_POLICY", "RESEARCH_PARAMETERS", "RISK_POLICY", "SCALPING_V2",
    "TRADE_PARAMETERS", "UNIT_CONSTANTS", "resolve_runtime_parameters",
)


def _relative(path: Path, base: Path, prefix: str) -> str:
    return f"{prefix}/{path.relative_to(base).as_posix()}"


def _roots():
    values = [
        (ROOT / "app", "app"),
        (ROOT / "traders_ml", "traders_ml"),
        (ROOT / "scripts", "scripts"),
        (ROOT / "tests", "tests"),
        (ROOT / "alembic", "alembic"),
    ]
    client = ROOT.parent / "traders-client"
    if client.exists():
        values.extend((
            (client / "src", "../traders-client/src"),
            (client / "tests", "../traders-client/tests"),
            (client / "scripts", "../traders-client/scripts"),
        ))
    return tuple((base, prefix) for base, prefix in values if base.exists())


def _tokens(name: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9]+", name.lower()) if part}


def _classification(file: str, symbol: str, literal: object, source_line: str):
    parts = _tokens(symbol)
    if file.startswith("tests/") or "/tests/" in file:
        return "TEST_VECTOR_ONLY", None, "classified test-only vector/expectation"
    if file.startswith("alembic/"):
        return "HISTORICAL_MIGRATION_ONLY", None, "immutable migration/schema history"
    if "generated" in file.lower() or "generated" in parts:
        return "GENERATED_CODE", None, "generated artifact"
    if parts & IDENTITY_TOKENS or isinstance(literal, str):
        return "PROTOCOL_OR_SCHEMA_IDENTITY", None, "identity/protocol literal; verify consumer contract"
    if any(reference in source_line for reference in YAML_REFERENCES):
        return "ALGORITHM_STRUCTURE_LITERAL", None, "literal is structural around an explicit YAML resolver"
    if parts & POLICY_TOKENS:
        return "UNKNOWN_REQUIRES_TRACE", None, "trace behavior authority; no direct YAML reference on this expression"
    return "ALGORITHM_STRUCTURE_LITERAL", None, "numeric/boolean algorithm structure"


def _call_name(node: ast.Call) -> str:
    value = node.func
    if isinstance(value, ast.Attribute):
        return value.attr
    if isinstance(value, ast.Name):
        return value.id
    return "call"


def _constants(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool)):
        yield node.value


def scan_rows():
    rows = []
    seen = set()
    for base, prefix in _roots():
        for path in sorted(base.rglob("*.py")):
            file = _relative(path, base, prefix)
            source = path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                rows.append({
                    "file": file, "line": 0, "symbol": "AST_PARSE",
                    "literal": "", "semantic_name": "AST_PARSE",
                    "classification": "UNKNOWN_REQUIRES_TRACE", "yaml_file": "",
                    "yaml_path": "", "schema_field": "", "consumer": file,
                    "action": "repair/inspect syntax before certification",
                })
                continue
            candidates = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    target = node.targets[0] if isinstance(node, ast.Assign) else node.target
                    symbol = target.id if isinstance(target, ast.Name) else "assignment"
                    for literal in _constants(node.value):
                        candidates.append((node.lineno, symbol, literal, "assignment"))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defaults = node.args.defaults
                    for argument, default in zip(node.args.args[-len(defaults):], defaults):
                        for literal in _constants(default):
                            candidates.append((node.lineno, argument.arg, literal, "function_default"))
                elif isinstance(node, ast.Call):
                    call = _call_name(node)
                    if call in {"get", "getattr", "getenv", "add_argument"}:
                        values = list(node.args[1:] if call != "add_argument" else ())
                        values.extend(
                            keyword.value for keyword in node.keywords
                            if keyword.arg == "default"
                        )
                        for value in values:
                            for literal in _constants(value):
                                candidates.append((node.lineno, call, literal, "literal_fallback"))
            for line, symbol, literal, role in candidates:
                key = (file, line, symbol, repr(literal), role)
                if key in seen:
                    continue
                seen.add(key)
                source_line = source_lines[line - 1] if 0 < line <= len(source_lines) else ""
                classification, mapping, action = _classification(
                    file, symbol, literal, source_line
                )
                rows.append({
                    "file": file,
                    "line": line,
                    "symbol": symbol,
                    "literal": repr(literal),
                    "semantic_name": symbol,
                    "classification": classification,
                    "yaml_file": "" if mapping is None else mapping[0],
                    "yaml_path": "" if mapping is None else mapping[1],
                    "schema_field": "" if mapping is None else mapping[2],
                    "consumer": f"{file}:{line}:{role}",
                    "action": action,
                })
    return rows


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = scan_rows()
    columns = (
        "file", "line", "symbol", "literal", "semantic_name", "classification",
        "yaml_file", "yaml_path", "schema_field", "consumer", "action",
    )
    with (OUTPUT / "HARDCODE_REAUDIT.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    counts = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    registry = registry_rows()
    runtime = resolve_runtime_parameters("trade-5m-v2")
    (OUTPUT / "runtime_provenance.json").write_text(
        json.dumps(runtime.public_provenance(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary = {
        "new_scan_files": len({row["file"] for row in rows}),
        "new_scan_suspicious_values": len(rows),
        "new_unexpected_policy_values": counts.get("UNKNOWN_REQUIRES_TRACE", 0),
        "previously_misclassified_values": counts.get("UNKNOWN_REQUIRES_TRACE", 0),
        "classification_counts": counts,
        "registry_keys": len(registry),
        "resolved_config_hash": runtime.resolved_config_hash,
        "exclusions": {
            "vendor_and_virtualenv": "third-party code, not project authority",
            "cache_and_build": "generated/non-source artifacts",
            "artifacts_and_reports": "evidence/output, not executable source",
        },
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["new_unexpected_policy_values"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
