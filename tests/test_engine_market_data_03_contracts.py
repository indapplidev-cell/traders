import ast
from pathlib import Path


def test_runtime_has_no_downstream_imports_or_trading_vocabulary():
    package = Path(__file__).parents[1] / "app" / "engine_market_data"
    forbidden_modules = {f"app.engine_{name}" for name in
                         ("analysis", "setup", "strategy", "risk", "execution", "position", "exit")}
    forbidden_terms = ("buy", "sell", "long", "short", "place_order", "execute_order",
                       "open_position", "close_position", "position_size", "calculate_risk",
                       "calculate_pnl", "profit_factor", "winrate", "api_key", "trade_signal",
                       "setup_candidate")
    for path in package.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom) and node.module]
        assert not any(name == blocked or name.startswith(blocked + ".")
                       for name in imports for blocked in forbidden_modules)
        assert not any(term in source.lower() for term in forbidden_terms)
