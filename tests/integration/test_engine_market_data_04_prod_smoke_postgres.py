import os
from pathlib import Path

import pytest

from app.engine_market_data.prod_smoke import ProdSmokeRunner


@pytest.mark.integration
@pytest.mark.requires_postgres
@pytest.mark.requires_network
def test_engine_market_data_04_real_postgres_and_binance_smoke_is_opt_in(tmp_path: Path):
    if os.environ.get("RUN_ENGINE_MARKET_DATA_04_PROD_SMOKE") != "1":
        pytest.skip("set RUN_ENGINE_MARKET_DATA_04_PROD_SMOKE=1 for the destructive-time live smoke")
    trace = ProdSmokeRunner(tmp_path, restart_wait_seconds=130).run()
    assert trace["final_verdict"] == "PROD_SMOKE_PASSED", trace
