import ast
from pathlib import Path
import app.engine_execution
import app.engine_paper
import app.engine_position as package

ROOT=Path(__file__).resolve().parents[2]
FILES=[*sorted((ROOT/"app"/"engine_position").glob("**/*.py")),ROOT/"scripts"/"engine_position_dry_run.py"]
TEXT="\n".join(p.read_text(encoding="utf-8").lower() for p in FILES)
IMPORTS={}
for path in FILES:
 tree=ast.parse(path.read_text(encoding="utf-8"))
 IMPORTS[path]={n.names[0].name.split('.')[0] if isinstance(n,ast.Import) else (n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))}
def test_69_no_network_imports(): assert not any(v&{"requests","httpx","aiohttp","websockets","socket","urllib"} for v in IMPORTS.values())
def test_70_no_docker_or_subprocess(): assert "docker" not in TEXT and not any("subprocess" in v for v in IMPORTS.values())
def test_71_no_credentials(): assert "binance_api_key" not in TEXT and "binance_api_secret" not in TEXT and "api_secret" not in TEXT
def test_72_no_database_imports(): assert not any(v&{"psycopg","sqlalchemy"} for v in IMPORTS.values())
def test_73_no_private_binance_calls(): assert all(x not in TEXT for x in ["create_order","order_market","order_limit","get_position_risk","futures_position_information","private websocket"])
def test_74_engine_execution_regression_import(): assert app.engine_execution.ExecutionMode.PAPER.value=="PAPER"
def test_75_engine_paper_regression_import(): assert hasattr(app.engine_paper,"PaperRunner")
def test_package_public_exports():
 required={"Position","PositionStatus","PositionSide","PositionEvent","PositionFillEvent","PositionMarkEvent","PositionCloseEvent","PositionCancelEvent","PositionTransitionResult","PositionLifecycleService","PositionStore","InMemoryPositionStore"}; assert required<=set(package.__all__)
