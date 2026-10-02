from __future__ import annotations

from pathlib import Path

from app.db.paper_models import (
    EmpiricalAuthorityGenerationRecord,
    EmpiricalRecoveryCampaignRecord,
    EmpiricalRecoveryEvaluationRecord,
)
from app.engine_paper.scalping_policy_v2 import (
    ADMISSION_REJECTED,
    EMPIRICAL_AUTHORITY_ESTABLISHED,
    EmpiricalSetupBucket,
    evaluate_expectancy,
)


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_RUNTIME_FILES = (
    "app/engine_paper/final_approval_materializer.py",
    "app/engine_paper/plan_execution_outcome.py",
    "app/engine_paper/production_approval.py",
    "app/engine_paper/scalping_paper_runner.py",
    "app/engine_paper/scalping_policy_v2.py",
    "app/engine_paper/scalping_shadow.py",
    "app/engine_paper/scalping_statistics.py",
    "app/operator_control/production_executor.py",
    "app/operator_control/runtime.py",
)


def test_exploration_and_requalification_have_no_active_runtime_branch() -> None:
    assert not (ROOT / "app/engine_paper/paper_exploration.py").exists()
    assert not (ROOT / "app/engine_paper/empirical_requalification.py").exists()
    for relative_path in ACTIVE_RUNTIME_FILES:
        source = (ROOT / relative_path).read_text(encoding="utf-8").lower()
        assert "paper_exploration" not in source
        assert "empirical_requalification" not in source


def test_negative_empirical_authority_is_diagnostic_above_dynamic_rr() -> None:
    decision = evaluate_expectancy(
        net_win_bps=300.0,
        net_loss_bps=100.0,
        bucket=EmpiricalSetupBucket(
            setup_type="SCALP_MOMENTUM_CONTINUATION",
            direction="BULLISH",
            samples=20,
            wins=7,
            bucket_key="rollback-negative-authority",
            average_win_net_bps=10.0,
            average_loss_net_bps=20.0,
        ),
    )

    assert decision.candidate_net_rr == 3.0
    assert decision.reason == "EMPIRICAL_SUFFICIENT_NEGATIVE_EV"
    assert decision.empirical_authority_status == EMPIRICAL_AUTHORITY_ESTABLISHED
    assert decision.admission_mode != ADMISSION_REJECTED
    assert decision.admitted
    assert not decision.empirical_pass


def test_0036_history_models_remain_readable_but_dormant() -> None:
    assert EmpiricalAuthorityGenerationRecord.__tablename__ == (
        "empirical_authority_generations"
    )
    assert EmpiricalRecoveryCampaignRecord.__tablename__ == (
        "empirical_recovery_campaigns"
    )
    assert EmpiricalRecoveryEvaluationRecord.__tablename__ == (
        "empirical_recovery_evaluations"
    )
