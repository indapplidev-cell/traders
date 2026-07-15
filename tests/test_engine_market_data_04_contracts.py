import ast
from pathlib import Path


def test_runtime_has_no_downstream_imports_or_synthetic_generation():
    root = Path(__file__).parents[1] / "app/engine_market_data"
    files = [root / name for name in ("continuous_sync_daemon.py", "continuous_sync_cli.py", "freshness_monitor.py")]
    source = "\n".join(path.read_text() for path in files)
    imports = [node.module for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom) and node.module]
    assert not any(name.startswith(("app.engine_analysis", "app.engine_setup", "app.engine_strategy", "app.engine_risk", "app.engine_paper")) for name in imports)
    assert "Candle(" not in (root / "continuous_sync_daemon.py").read_text()
