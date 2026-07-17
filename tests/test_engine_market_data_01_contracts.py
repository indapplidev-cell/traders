import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "app" / "engine_market_data"
FORBIDDEN_IMPORTS = {
    "app.engine_analysis", "app.engine_setup", "app.engine_strategy", "app.engine_risk",
    "app.engine_execution", "app.engine_position", "app.engine_exit",
}


def test_market_data_package_does_not_import_downstream_engines() -> None:
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        assert not any(any(name == forbidden or name.startswith(forbidden + ".") for forbidden in FORBIDDEN_IMPORTS) for name in imports)


def test_module_contains_no_trading_concepts_or_credentials() -> None:
    python_source = "\n".join(path.read_text(encoding="utf-8").lower() for path in PACKAGE.glob("*.py"))
    for forbidden in ("api_key", "secret_key", "place_order", "trade_signal", "setup_candidate", "calculate_pnl"):
        assert forbidden not in python_source
