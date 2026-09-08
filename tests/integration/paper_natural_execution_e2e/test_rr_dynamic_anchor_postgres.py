from sqlalchemy import text

from scripts.forensic_scalping_rr_dynamic_anchor import EXPECTED_SYMBOLS, freeze_cohort, select_latest_completed_cycle
from tests.test_scalping_rr_dynamic_anchor_forensic import row


def test_postgres_history_freezes_anchor_and_detects_last_pass(natural_e2e_engine):
    anchor = 1_788_900_000_000
    values = []
    for boundary, outcome in ((anchor - 600_000, "PASS"), (anchor - 300_000, "REJECT"), (anchor, "REJECT")):
        for index, symbol in enumerate(sorted(EXPECTED_SYMBOLS)):
            values.append(row(boundary, symbol, result=outcome if index == 0 else None))
    with natural_e2e_engine.begin() as connection:
        connection.execute(text("CREATE TEMP TABLE rr_forensic_history (payload jsonb NOT NULL)"))
        connection.execute(text("INSERT INTO rr_forensic_history(payload) VALUES (CAST(:payload AS jsonb))"),
                           [{"payload": __import__("json").dumps(value)} for value in values])
        persisted = [item[0] for item in connection.execute(text("SELECT payload FROM rr_forensic_history"))]
        resolved_anchor, _ = select_latest_completed_cycle(persisted)
        frozen, _ = freeze_cohort(persisted, resolved_anchor)
        new_values = [row(anchor + 300_000, symbol, result="PASS" if index == 0 else None)
                      for index, symbol in enumerate(sorted(EXPECTED_SYMBOLS))]
        connection.execute(text("INSERT INTO rr_forensic_history(payload) VALUES (CAST(:payload AS jsonb))"),
                           [{"payload": __import__("json").dumps(value)} for value in new_values])
        changed = [item[0] for item in connection.execute(text("SELECT payload FROM rr_forensic_history"))]
    frozen_after, _ = freeze_cohort(changed, resolved_anchor)
    assert [item["candidate_id"] for item in frozen] == [item["candidate_id"] for item in frozen_after]
    assert [item["rr_result"] for item in frozen] == ["PASS", "REJECT", "REJECT"]
