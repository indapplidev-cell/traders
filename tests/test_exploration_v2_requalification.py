from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.paper_models import (
    EmpiricalAuthorityGenerationRecord,
    EmpiricalRecoveryCampaignRecord,
    EmpiricalRecoveryEvaluationRecord,
)
from app.engine_paper.empirical_requalification import (
    EXPLORATION_V2_ADMISSION_MODE,
    EXPLORATION_V2_POLICY_VERSION,
    EmpiricalRequalificationStore,
    RecoveryObservation,
    authority_metrics,
    recovery_window,
    requalification_predicate,
)
from app.engine_paper.paper_exploration import exploration_eligible
from app.engine_paper.scalping_policy_v2 import (
    EMPIRICAL_AUTHORITY_ESTABLISHED,
    EmpiricalSetupBucket,
    ExpectancyDecision,
    evaluate_expectancy,
)


POPULATION = "empirical-authority-population-v1:requalification-test"
START = datetime(2026, 9, 29, 8, tzinfo=timezone.utc)


def _decision(**changes: object) -> ExpectancyDecision:
    values: dict[str, object] = {
        "admitted": False,
        "expected_value_bps": -10.0,
        "probability": 0.25,
        "reason": "EMPIRICAL_SUFFICIENT_NEGATIVE_EV",
        "dynamic_required_net_rr": 2.75,
        "candidate_net_rr": 0.60,
        "empirical_authority_status": EMPIRICAL_AUTHORITY_ESTABLISHED,
        "empirical_ev_net_bps": -10.0,
        "authority_population_id": POPULATION,
        "authority_observation_set_fingerprint": "a" * 64,
    }
    values.update(changes)
    return ExpectancyDecision(**values)


def test_v2_reproduces_v1_failure_but_keeps_base_rr_and_other_gates() -> None:
    common = dict(
        profile_id="trade-5m-v2", execution_mode="PAPER", enabled=True,
        minimum_planned_rr=0.476, policy_version=EXPLORATION_V2_POLICY_VERSION,
    )
    assert exploration_eligible(_decision(), candidate_net_rr=0.60, **common)
    assert not exploration_eligible(_decision(), candidate_net_rr=0.47, **common)
    assert not exploration_eligible(
        _decision(reason="ECONOMIC_GEOMETRY_NOT_FEASIBLE"),
        candidate_net_rr=3.0, **common,
    )


def _observation(
    index: int, value: float, *, probe: bool = False,
    symbol: str = "BTCUSDT", at: datetime | None = None,
) -> RecoveryObservation:
    return RecoveryObservation(
        position_id=f"position:{index}",
        symbol=symbol,
        closed_at=at or (START + timedelta(minutes=index)),
        net_return_bps=value,
        admission_mode=(
            EXPLORATION_V2_ADMISSION_MODE if probe else "NORMAL_EMPIRICAL_ADMISSION"
        ),
        exploration_policy_version=(
            EXPLORATION_V2_POLICY_VERSION if probe else None
        ),
    )


def _baseline() -> tuple[RecoveryObservation, ...]:
    # Negative established authority; oldest losses deliberately leave first.
    values = [-10.0] * 8 + [10.0] * 7 + [-10.0] * 5
    return tuple(_observation(index, value) for index, value in enumerate(values))


def _bucket() -> EmpiricalSetupBucket:
    return EmpiricalSetupBucket(
        setup_type="SCALP_MOMENTUM_CONTINUATION", direction="MIXED",
        samples=20, wins=7, level="setup",
        bucket_key="setup:SCALP_MOMENTUM_CONTINUATION",
        average_win_net_bps=10.0, average_loss_net_bps=10.0,
        authority_population_id=POPULATION,
        observation_set_fingerprint="b" * 64,
    )


def _probes(count: int, *, final_value: float = 100.0) -> tuple[RecoveryObservation, ...]:
    values = [100.0] * count
    if values:
        values[-1] = final_value
    symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    return tuple(
        _observation(
            100 + index, value, probe=True, symbol=symbols[index % 3],
            at=START + timedelta(hours=1, minutes=index),
        )
        for index, value in enumerate(values)
    )


def test_recovery_window_is_latest_20_without_history_mutation() -> None:
    original = _baseline()
    combined = original + _probes(3)
    window = recovery_window(combined)
    assert len(window) == 20
    assert tuple(item.position_id for item in window[:2]) == ("position:3", "position:4")
    assert len(combined) == 23
    assert tuple(item.net_return_bps for item in original) == (
        -10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0, -10.0,
        10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0,
        -10.0, -10.0, -10.0, -10.0, -10.0,
    )


def test_requalification_predicate_requires_probe_count_and_symbol_diversity() -> None:
    metrics = authority_metrics(
        recovery_window(_baseline() + _probes(8)),
        bucket_level="setup", bucket_key="setup:test",
        authority_population_id=POPULATION,
    )
    assert metrics is not None and metrics.empirical_ev_net_bps > 0
    assert requalification_predicate(metrics, new_v2_probes=7, distinct_symbols=3)[0] is False
    assert requalification_predicate(metrics, new_v2_probes=8, distinct_symbols=2)[0] is False
    assert requalification_predicate(metrics, new_v2_probes=8, distinct_symbols=3)[0] is True


@pytest.fixture
def authority_store(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAPER_EXPLORATION_POLICY_VERSION", EXPLORATION_V2_POLICY_VERSION)
    monkeypatch.setenv("EMPIRICAL_REQUALIFICATION_ENABLED", "true")
    monkeypatch.setenv("EMPIRICAL_REQUALIFICATION_POLICY_VERSION", "empirical-requalification-v1")
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = (
        EmpiricalAuthorityGenerationRecord.__table__,
        EmpiricalRecoveryCampaignRecord.__table__,
        EmpiricalRecoveryEvaluationRecord.__table__,
    )
    for table in tables:
        table.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield EmpiricalRequalificationStore(factory), factory
    engine.dispose()


def test_two_distinct_windows_promote_once_and_restart_is_idempotent(authority_store) -> None:
    store, factory = authority_store
    base = _baseline()
    _, initial = store.reconcile(base_bucket=_bucket(), observations=base, now=START + timedelta(minutes=30))
    assert initial.authority_state == "EXPLORATION_RECOVERY_ACTIVE"

    _, first = store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(8),
        now=START + timedelta(hours=2),
    )
    assert first.recovery_new_observation_count == 8
    assert first.recovery_distinct_symbol_count == 3
    assert first.recovery_positive_confirmation_count == 1
    assert first.authority_state == "EXPLORATION_RECOVERY_ACTIVE"

    active_bucket, second = store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(9),
        now=START + timedelta(hours=2, minutes=1),
    )
    assert second.recovery_positive_confirmation_count == 2
    assert second.authority_state == "REQUALIFIED_ACTIVE"
    assert active_bucket.observation_set_fingerprint == second.recovery_window_fingerprint
    normal = evaluate_expectancy(
        net_win_bps=300.0, net_loss_bps=100.0, bucket=active_bucket,
    )
    assert normal.admitted

    replay_bucket, replay = store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(9),
        now=START + timedelta(hours=2, minutes=2),
    )
    assert replay.authority_generation_id == second.authority_generation_id
    assert replay_bucket.observation_set_fingerprint == active_bucket.observation_set_fingerprint
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(EmpiricalRecoveryEvaluationRecord)) == 9
        assert session.scalar(select(func.count()).select_from(EmpiricalAuthorityGenerationRecord)) == 2
        assert session.scalar(select(func.count()).select_from(EmpiricalRecoveryCampaignRecord)) == 1


def test_positive_confirmation_resets_when_next_window_fails(authority_store) -> None:
    store, _ = authority_store
    base = _baseline()
    store.reconcile(base_bucket=_bucket(), observations=base, now=START + timedelta(minutes=30))
    _, first = store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(8),
        now=START + timedelta(hours=2),
    )
    assert first.recovery_positive_confirmation_count == 1
    _, failed = store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(9, final_value=-1000.0),
        now=START + timedelta(hours=2, minutes=1),
    )
    assert failed.recovery_positive_confirmation_count == 0
    assert failed.authority_state == "EXPLORATION_RECOVERY_ACTIVE"


def test_negative_recent_authority_starts_new_campaign(authority_store) -> None:
    store, factory = authority_store
    base = _baseline()
    store.reconcile(base_bucket=_bucket(), observations=base, now=START + timedelta(minutes=30))
    store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(9),
        now=START + timedelta(hours=2),
    )
    losses = tuple(
        _observation(
            200 + index, 10.0 if index == 0 else -50.0, symbol="BTCUSDT",
            at=START + timedelta(hours=3, minutes=index),
        )
        for index in range(20)
    )
    _, snapshot = store.reconcile(
        base_bucket=_bucket(), observations=base + _probes(9) + losses,
        now=START + timedelta(hours=4),
    )
    assert snapshot.authority_state == "EXPLORATION_RECOVERY_ACTIVE"
    with factory() as session:
        campaigns = tuple(session.scalars(
            select(EmpiricalRecoveryCampaignRecord).order_by(
                EmpiricalRecoveryCampaignRecord.started_at
            )
        ))
        assert len(campaigns) == 2
        assert campaigns[0].state == "REQUALIFIED_ACTIVE"
        assert campaigns[1].state == "EXPLORATION_RECOVERY_ACTIVE"
