"""Prevent new cross-profile online result associations.

Revision ID: 0019_first_class_15m_domain
Revises: 0018_promote_5m_production_search

The trigger is deliberately forward-only: it validates every new or changed
result while preserving the quarantined historical forensic mismatch.
"""

from alembic import op


revision = "0019_first_class_15m_domain"
down_revision = "0018_promote_5m_production_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_online_pipeline_result_domain_identity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM online_pipeline_runs r
                WHERE r.run_id = NEW.run_id
                  AND r.trade_profile_id = NEW.trade_profile_id
                  AND r.profile_mode = NEW.profile_mode
                  AND r.symbol = NEW.symbol
                  AND r.primary_timeframe = NEW.primary_timeframe
                  AND r.closed_until_ms = NEW.closed_until_ms
            ) THEN
                RAISE EXCEPTION 'online pipeline execution-domain identity mismatch'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_online_pipeline_result_domain_identity
        BEFORE INSERT OR UPDATE OF
            run_id, trade_profile_id, profile_mode, symbol,
            primary_timeframe, closed_until_ms
        ON online_pipeline_results
        FOR EACH ROW
        EXECUTE FUNCTION enforce_online_pipeline_result_domain_identity()
    """)
