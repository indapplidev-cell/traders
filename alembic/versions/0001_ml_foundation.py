"""Create initial traders-ml foundation schema.

Revision ID: 0001_ml_foundation
Revises:
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_ml_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_candles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("quote_asset_volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("number_of_trades", sa.Integer(), nullable=False),
        sa.Column("taker_buy_base_volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("taker_buy_quote_volume", sa.Numeric(20, 8), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("symbol", "interval", "open_time", name="uq_market_candles_s_i_ot"),
    )

    op.create_table(
        "ml_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_version", sa.String(length=50), nullable=False),
        sa.Column("features_json", sa.JSON(), nullable=False),
        sa.Column("features_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint(
            "symbol",
            "interval",
            "candle_open_time",
            "feature_version",
            name="uq_ml_features_s_i_cot_fv",
        ),
    )

    op.create_table(
        "ml_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_candles", sa.Integer(), nullable=False),
        sa.Column("direction_label", sa.String(length=20), nullable=False),
        sa.Column("tp_before_sl", sa.Boolean(), nullable=True),
        sa.Column("future_return", sa.Numeric(20, 8), nullable=False),
        sa.Column("future_move_atr", sa.Numeric(20, 8), nullable=False),
        sa.Column("max_favorable_move_atr", sa.Numeric(20, 8), nullable=False),
        sa.Column("max_adverse_move_atr", sa.Numeric(20, 8), nullable=False),
        sa.Column("label_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint(
            "symbol",
            "interval",
            "candle_open_time",
            "horizon_candles",
            "label_version",
            name="uq_ml_labels_s_i_cot_hc_lv",
        ),
    )

    op.create_table(
        "ml_training_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("horizon_candles", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_table(
        "ml_model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("horizon_candles", sa.Integer(), nullable=False),
        sa.Column("feature_version", sa.String(length=50), nullable=False),
        sa.Column("label_version", sa.String(length=50), nullable=False),
        sa.Column("artifact_path", sa.String(length=255), nullable=False),
        sa.Column("train_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("test_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("test_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accuracy", sa.Numeric(10, 6), nullable=True),
        sa.Column("precision_up", sa.Numeric(10, 6), nullable=True),
        sa.Column("precision_down", sa.Numeric(10, 6), nullable=True),
        sa.Column("brier_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("tp_before_sl_accuracy", sa.Numeric(10, 6), nullable=True),
        sa.Column("profit_factor", sa.Numeric(10, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_candles", sa.Integer(), nullable=False),
        sa.Column("prob_up", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_down", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_flat", sa.Numeric(10, 6), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("tp_before_sl_probability", sa.Numeric(10, 6), nullable=True),
        sa.Column("expected_move_atr", sa.Numeric(10, 6), nullable=True),
        sa.Column("risk_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("confidence", sa.Numeric(10, 6), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "ml_replay_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    op.create_table(
        "ml_replay_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("interval", sa.String(length=20), nullable=False),
        sa.Column("candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_direction", sa.String(length=20), nullable=False),
        sa.Column("actual_direction", sa.String(length=20), nullable=False),
        sa.Column("prob_up", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_down", sa.Numeric(10, 6), nullable=False),
        sa.Column("prob_flat", sa.Numeric(10, 6), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("error_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ml_replay_results")
    op.drop_table("ml_replay_sessions")
    op.drop_table("ml_predictions")
    op.drop_table("ml_model_versions")
    op.drop_table("ml_training_runs")
    op.drop_table("ml_labels")
    op.drop_table("ml_features")
    op.drop_table("market_candles")
