import ast
from pathlib import Path


def test_runtime_has_no_downstream_imports_or_trading_operations():
    package = Path(__file__).parents[1] / "app/engine_market_data"
    forbidden_imports = {f"app.engine_{name}" for name in ("analysis", "setup", "strategy", "risk", "execution", "position", "exit")}
    forbidden_words = ("place_order", "execute_order", "open_position", "close_position", "position_size", "calculate_risk", "calculate_pnl", "profit_factor", "winrate")
    for path in package.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
        assert not any(any(name == item or name.startswith(item + ".") for item in forbidden_imports) for name in imports)
        assert not any(word in source.lower() for word in forbidden_words)
