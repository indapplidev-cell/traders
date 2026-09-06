"""Reconcile least-privilege grants for scalping profitability tables.

Revision ID: 0028_scalping_profitability_grants
Revises: 0027_scalping_profitability_integration
"""

from alembic import op


revision = "0028_scalping_profitability_grants"
down_revision = "0027_scalping_profitability_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $grants$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'traders_paper_runtime') THEN
                GRANT SELECT, INSERT, UPDATE ON TABLE scalping_opportunities
                    TO traders_paper_runtime;
                GRANT SELECT, INSERT ON TABLE scalping_outcome_diagnostics
                    TO traders_paper_runtime;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'traders_readonly_api') THEN
                GRANT SELECT ON TABLE scalping_opportunities, scalping_outcome_diagnostics
                    TO traders_readonly_api;
            END IF;
        END
        $grants$;
        """
    )


def downgrade() -> None:
    raise RuntimeError("0028 Scalping profitability grants are forward-only")
