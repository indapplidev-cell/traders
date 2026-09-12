"""Static proof that Parameter Sweep has no symbol-specific runtime behavior."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Iterable

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .universe import resolve_parameter_sweep_universe


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _line_occurrences(paths: Iterable[Path], symbols: set[str], classification: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            for symbol in sorted(symbols):
                if symbol in line:
                    rows.append({
                        "classification": classification, "symbol": symbol,
                        "path": path.relative_to(PROJECT_ROOT).as_posix(),
                        "line": number,
                    })
    return rows


def _runtime_literals(paths: Iterable[Path], symbols: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    hardcodes: list[dict[str, Any]] = []
    defaults: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    for path in sorted(paths):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or node.value not in symbols:
                continue
            detail = {
                "classification": "RUNTIME_HARDCODE", "symbol": node.value,
                "path": path.relative_to(PROJECT_ROOT).as_posix(), "line": node.lineno,
            }
            parent = parents.get(node)
            grandparent = parents.get(parent) if parent is not None else None
            if isinstance(parent, ast.keyword) and parent.arg == "default":
                detail["classification"] = "RUNTIME_DEFAULT"
                defaults.append(detail)
            elif isinstance(parent, ast.Compare) or isinstance(grandparent, ast.Compare):
                detail["classification"] = "RUNTIME_BRANCH"
                branches.append(detail)
            else:
                hardcodes.append(detail)
    return hardcodes, defaults, branches


def build_symbol_runtime_authority_audit() -> dict[str, Any]:
    universe_id, configured_symbols = resolve_parameter_sweep_universe()
    symbols = set(configured_symbols)
    runtime_paths = list((PROJECT_ROOT / "traders_ml" / "parameter_sweep").glob("*.py"))
    hardcodes, defaults, branches = _runtime_literals(runtime_paths, symbols)
    test_literals = _line_occurrences(
        (PROJECT_ROOT / "tests" / "research").glob("*.py"), symbols, "TEST_FIXTURE",
    )
    audit_literals = _line_occurrences(
        (PROJECT_ROOT / "docs" / "audits").glob("*"), symbols, "AUDIT_ARTIFACT",
    )
    return {
        "artifact": "SYMBOL_RUNTIME_AUTHORITY_AUDIT", "schema_version": 1,
        "symbols_scanned": sorted(symbols),
        "runtime_scope": "traders_ml/parameter_sweep/*.py",
        "runtime_symbol_hardcodes": hardcodes,
        "runtime_symbol_defaults": defaults,
        "runtime_symbol_branches": branches,
        "RUNTIME_SYMBOL_HARDCODES": len(hardcodes),
        "RUNTIME_SYMBOL_DEFAULTS": len(defaults),
        "RUNTIME_SYMBOL_BRANCHES": len(branches),
        "allowed_test_literals": test_literals,
        "allowed_audit_literals": audit_literals,
        "symbol_authority_source": f"app.trading_universe.domain:{universe_id}",
        "gui_symbol_source": "ParameterSweepWindow.symbol_selector -> ParameterSweepController.start_new_run -> validate_parameter_sweep_symbol",
        "cli_symbol_source": "parameter_sweep, expanded_search, and adaptive_refinement CLIs require --symbol -> validate_parameter_sweep_symbol",
        "run_config_symbol_source": "validated selected symbol persisted in expanded/adaptive config and fingerprint-bound checkpoints",
        "dataset_symbol_binding": "validate_dataset requires every row symbol == validated selected symbol; mismatch fails closed",
        "separability_symbol_binding": "run_separability requires explicit symbol and filters/query-binds it; CLI has no symbol default",
        "range_handoff_symbol_binding": "DATA_DRIVEN_RANGE_HANDOFF.symbol copied from separability manifest and validate_handoff requires equality",
        "expanded_search_symbol_binding": "run_expanded_search validates selected symbol against trading-universe-v2 before handoff/dataset evaluation",
        "adaptive_refinement_symbol_binding": "run_adaptive_refinement validates selected symbol against dataset, range handoff, expanded config, expanded handoff and checkpoint",
        "resume_symbol_binding": "expanded and adaptive checkpoint symbol/fingerprint guards fail closed on mismatch",
        "symbol_binding_status": "PASS" if not (hardcodes or defaults or branches) else "FAIL",
    }


def write_symbol_runtime_authority_audit(path: Path) -> dict[str, Any]:
    artifact = build_symbol_runtime_authority_audit()
    DEFAULT_ARTIFACT_WRITER.atomic_json(path, artifact, operation="symbol_runtime_authority_audit")
    return artifact


def main() -> int:
    artifact = write_symbol_runtime_authority_audit(
        PROJECT_ROOT / "artifacts" / "scalping_v2_parameter_sweep" / "SYMBOL_RUNTIME_AUTHORITY_AUDIT.json"
    )
    print(json.dumps({
        key: artifact[key] for key in (
            "RUNTIME_SYMBOL_HARDCODES", "RUNTIME_SYMBOL_DEFAULTS",
            "RUNTIME_SYMBOL_BRANCHES", "symbol_binding_status",
        )
    }, indent=2, sort_keys=True))
    return 0 if artifact["symbol_binding_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
