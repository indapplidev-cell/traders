from app.server_api.repositories.sqlalchemy_read import canonical_paper_exit_reason
from app.server_api.services.paper_reporting import _default_control_status


def test_persisted_exit_decision_replaces_generic_position_close_reason() -> None:
    assert canonical_paper_exit_reason(
        "PAPER_POSITION_CLOSED", "TAKE_PROFIT"
    ) == "TAKE_PROFIT"
    assert canonical_paper_exit_reason(
        "PAPER_POSITION_CLOSED", "STOP_LOSS"
    ) == "STOP_LOSS"
    assert canonical_paper_exit_reason(
        "PAPER_POSITION_CLOSED", None
    ) == "PAPER_POSITION_CLOSED"


def test_absent_audit_subsystem_is_explicitly_not_applicable() -> None:
    value = _default_control_status()
    assert value.audit_health == "NOT_APPLICABLE"
    assert value.state_audit_reconciliation == "NOT_APPLICABLE"
    assert "UNKNOWN" not in value.model_dump_json()
