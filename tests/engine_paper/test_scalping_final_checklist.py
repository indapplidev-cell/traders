from app.engine_paper.scalping_final_checklist import evaluate_scalping_final_checklist


def facts(**changes):
    value = dict(
        market_data_fresh=True, setup_valid=True, strategy_admitted=True,
        geometry_valid=True, target_valid=True, cost_gate_pass=True,
        risk_pass=True, opportunity_not_duplicate=True, singleton_valid=True,
        entry_still_valid=True, authority_valid=True,
    )
    value.update(changes)
    return value


def test_final_approval_is_only_a_complete_boolean_checklist():
    result = evaluate_scalping_final_checklist(**facts())
    assert result.passed is True
    assert result.to_dict()["passed"] is True


def test_each_failed_prerequisite_fails_the_checklist_without_rescoring():
    for name in facts():
        assert evaluate_scalping_final_checklist(**facts(**{name: False})).passed is False
