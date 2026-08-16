from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import subprocess
import sys

import pytest

from app.engine_risk.risk_decision import risk_decision_id
from app.engine_safety.paper_domain import PaperDomainError, require_identity
from app.engine_strategy.lineage_identity import (
    BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION,
    bounded_lineage_identity,
)
from app.engine_strategy.strategy_decision import (
    canonical_strategy_decision_identity,
    strategy_decision_id,
)


SYMBOL = "AVAXUSDT"
TIMEFRAME = "15m"
BOUNDARY = 1_786_891_500_000
SETUP_ID = (
    "setup:AVAXUSDT:15m:1786891500000:BREAKOUT_CONTINUATION:"
    "SETUP_CANDIDATE:09b38de71b8e518d"
)


def test_current_140_character_production_identity_reproduces_old_validator_failure():
    canonical = canonical_strategy_decision_identity(
        SYMBOL, TIMEFRAME, BOUNDARY, SETUP_ID
    )
    old = f"strategy:{canonical}:{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"
    assert len(old) == 140
    with pytest.raises(PaperDomainError) as failure:
        require_identity(old, "causation_id")
    assert failure.value.reason_code.value == "PAPER_INPUT_IDENTITY_INVALID"


@pytest.mark.parametrize("canonical_length", (127, 128, 129, 140, 10_000))
def test_bounded_identity_length_contract_for_boundary_and_very_long_values(
    canonical_length: int,
):
    value = bounded_lineage_identity("strategy:v2", "Ж" * canonical_length)
    assert len(value) == 76
    assert len(value) <= 128
    assert value.isascii()


def test_same_canonical_lineage_is_deterministic_concurrent_and_process_restart_stable():
    canonical = canonical_strategy_decision_identity(
        SYMBOL, TIMEFRAME, BOUNDARY, SETUP_ID
    )
    expected = strategy_decision_id(SYMBOL, TIMEFRAME, BOUNDARY, SETUP_ID)
    with ThreadPoolExecutor(max_workers=8) as pool:
        concurrent = tuple(
            pool.map(
                lambda _: strategy_decision_id(SYMBOL, TIMEFRAME, BOUNDARY, SETUP_ID),
                range(64),
            )
        )
    assert set(concurrent) == {expected}
    script = (
        "from app.engine_strategy.strategy_decision import strategy_decision_id;"
        f"print(strategy_decision_id({SYMBOL!r},{TIMEFRAME!r},{BOUNDARY!r},{SETUP_ID!r}))"
    )
    restarted = subprocess.check_output(
        [sys.executable, "-c", script], text=True
    ).strip()
    assert restarted == expected
    assert expected == bounded_lineage_identity("strategy:v2", canonical)
    assert BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION == "bounded-lineage-sha256-v1"


def test_different_run_candidate_symbol_and_boundary_lineage_separate():
    base = bounded_lineage_identity("strategy:v2", "run:1|candidate:1|AVAXUSDT|1")
    variants = {
        bounded_lineage_identity("strategy:v2", "run:2|candidate:1|AVAXUSDT|1"),
        bounded_lineage_identity("strategy:v2", "run:1|candidate:2|AVAXUSDT|1"),
        bounded_lineage_identity("strategy:v2", "run:1|candidate:1|BTCUSDT|1"),
        bounded_lineage_identity("strategy:v2", "run:1|candidate:1|AVAXUSDT|2"),
    }
    assert base not in variants
    assert len(variants) == 4


def test_production_shape_strategy_and_derived_risk_public_identities_fit_contract():
    strategy_id = strategy_decision_id(SYMBOL, TIMEFRAME, BOUNDARY, SETUP_ID)
    risk_id = risk_decision_id(SYMBOL, TIMEFRAME, BOUNDARY, strategy_id)
    assert len(strategy_id) == 76
    assert len(risk_id) == 125
    assert require_identity(strategy_id, "decision_id") == strategy_id
    assert require_identity(risk_id, "risk_decision_id") == risk_id

