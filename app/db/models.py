from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketCandles(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint("symbol", "interval", "open_time", name="uq_market_candles_s_i_ot"),
        Index("ix_market_candles_symbol_interval_open_time", "symbol", "interval", "open_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    quote_asset_volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    number_of_trades: Mapped[int] = mapped_column(nullable=False)
    taker_buy_base_volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    taker_buy_quote_volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MlFeatures(Base):
    __tablename__ = "ml_features"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "interval",
            "candle_open_time",
            "feature_version",
            name="uq_ml_features_s_i_cot_fv",
        ),
        Index("ix_ml_features_symbol_interval_cot_fv", "symbol", "interval", "candle_open_time", "feature_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    features_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MlLabels(Base):
    __tablename__ = "ml_labels"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "interval",
            "candle_open_time",
            "horizon_candles",
            "label_version",
            name="uq_ml_labels_s_i_cot_hc_lv",
        ),
        Index(
            "ix_ml_labels_symbol_interval_cot_hc_lv",
            "symbol",
            "interval",
            "candle_open_time",
            "horizon_candles",
            "label_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_candles: Mapped[int] = mapped_column(nullable=False)
    direction_label: Mapped[str] = mapped_column(String(20), nullable=False)
    tp_before_sl: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    future_return: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    future_move_atr: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    max_favorable_move_atr: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    max_adverse_move_atr: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    label_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MlTrainingRuns(Base):
    __tablename__ = "ml_training_runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_ml_training_runs_run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    horizon_candles: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)


class MlModelVersions(Base):
    __tablename__ = "ml_model_versions"
    __table_args__ = (
        UniqueConstraint("model_version", name="uq_ml_model_versions_model_version"),
        Index("ix_ml_model_versions_symbol_interval_horizon_active", "symbol", "interval", "horizon_candles", "is_active"),
        Index(
            "uq_ml_model_versions_active_scope",
            "symbol",
            "interval",
            "horizon_candles",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    horizon_candles: Mapped[int] = mapped_column(nullable=False)
    feature_version: Mapped[str] = mapped_column(String(50), nullable=False)
    label_version: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(255), nullable=False)
    train_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    train_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validation_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    test_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    test_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Numeric(10, 6))
    precision_up: Mapped[float | None] = mapped_column(Numeric(10, 6))
    precision_down: Mapped[float | None] = mapped_column(Numeric(10, 6))
    brier_score: Mapped[float | None] = mapped_column(Numeric(10, 6))
    tp_before_sl_accuracy: Mapped[float | None] = mapped_column(Numeric(10, 6))
    profit_factor: Mapped[float | None] = mapped_column(Numeric(10, 6))
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(10, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MlPredictions(Base):
    __tablename__ = "ml_predictions"
    __table_args__ = (
        Index("ix_ml_predictions_symbol_interval_candle_open_time", "symbol", "interval", "candle_open_time"),
        Index("ix_ml_predictions_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_candles: Mapped[int] = mapped_column(nullable=False)
    prob_up: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    prob_down: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    prob_flat: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    tp_before_sl_probability: Mapped[float | None] = mapped_column(Numeric(10, 6))
    expected_move_atr: Mapped[float | None] = mapped_column(Numeric(10, 6))
    risk_score: Mapped[float | None] = mapped_column(Numeric(10, 6))
    confidence: Mapped[float | None] = mapped_column(Numeric(10, 6))
    request_payload: Mapped[dict | None] = mapped_column(JSON)
    response_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MlReplaySessions(Base):
    __tablename__ = "ml_replay_sessions"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_ml_replay_sessions_session_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MlReplayResults(Base):
    __tablename__ = "ml_replay_results"
    __table_args__ = (
        Index("ix_ml_replay_results_session_id", "session_id"),
        Index("ix_ml_replay_results_model_symbol_interval_cot", "model_version", "symbol", "interval", "candle_open_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    prob_up: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    prob_down: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    prob_flat: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_score: Mapped[float | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
