"""Add constraints and indexes for ML runtime tables.

Revision ID: 0003_constraints_indexes
Revises: 0002_make_tp_before_sl_nullable
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_constraints_indexes"
down_revision = "0002_make_tp_before_sl_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_ml_model_versions_model_version", "ml_model_versions", ["model_version"])
    op.create_unique_constraint("uq_ml_training_runs_run_id", "ml_training_runs", ["run_id"])
    op.create_unique_constraint("uq_ml_replay_sessions_session_id", "ml_replay_sessions", ["session_id"])

    op.create_index("ix_market_candles_symbol_interval_open_time", "market_candles", ["symbol", "interval", "open_time"])
    op.create_index(
        "ix_ml_features_symbol_interval_cot_fv",
        "ml_features",
        ["symbol", "interval", "candle_open_time", "feature_version"],
    )
    op.create_index(
        "ix_ml_labels_symbol_interval_cot_hc_lv",
        "ml_labels",
        ["symbol", "interval", "candle_open_time", "horizon_candles", "label_version"],
    )
    op.create_index(
        "ix_ml_predictions_symbol_interval_candle_open_time",
        "ml_predictions",
        ["symbol", "interval", "candle_open_time"],
    )
    op.create_index("ix_ml_predictions_model_version", "ml_predictions", ["model_version"])
    op.create_index("ix_ml_replay_results_session_id", "ml_replay_results", ["session_id"])
    op.create_index(
        "ix_ml_replay_results_model_symbol_interval_cot",
        "ml_replay_results",
        ["model_version", "symbol", "interval", "candle_open_time"],
    )
    op.create_index(
        "ix_ml_model_versions_symbol_interval_horizon_active",
        "ml_model_versions",
        ["symbol", "interval", "horizon_candles", "is_active"],
    )
    op.create_index(
        "uq_ml_model_versions_active_scope",
        "ml_model_versions",
        ["symbol", "interval", "horizon_candles"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_ml_model_versions_active_scope", table_name="ml_model_versions")
    op.drop_index("ix_ml_model_versions_symbol_interval_horizon_active", table_name="ml_model_versions")
    op.drop_index("ix_ml_replay_results_model_symbol_interval_cot", table_name="ml_replay_results")
    op.drop_index("ix_ml_replay_results_session_id", table_name="ml_replay_results")
    op.drop_index("ix_ml_predictions_model_version", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_symbol_interval_candle_open_time", table_name="ml_predictions")
    op.drop_index("ix_ml_labels_symbol_interval_cot_hc_lv", table_name="ml_labels")
    op.drop_index("ix_ml_features_symbol_interval_cot_fv", table_name="ml_features")
    op.drop_index("ix_market_candles_symbol_interval_open_time", table_name="market_candles")

    op.drop_constraint("uq_ml_replay_sessions_session_id", "ml_replay_sessions", type_="unique")
    op.drop_constraint("uq_ml_training_runs_run_id", "ml_training_runs", type_="unique")
    op.drop_constraint("uq_ml_model_versions_model_version", "ml_model_versions", type_="unique")
