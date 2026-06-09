from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class PredictionCandleInput(BaseModel):
    open_time: str
    open: str
    high: str
    low: str
    close: str
    volume: str
    quote_asset_volume: str | None = None
    number_of_trades: int | None = None
    taker_buy_base_volume: str | None = None
    taker_buy_quote_volume: str | None = None


class PredictionContextInput(BaseModel):
    market_regime: str | None = None
    strategy_signal: str | None = None
    risk_profile: str | None = None


class PredictionRequest(BaseModel):
    symbol: str
    interval: str
    horizon_candles: int
    candles: list[PredictionCandleInput]
    context: PredictionContextInput | None = None


class PredictionResponse(BaseModel):
    ml_available: bool
    reason: str | None = None
    symbol: str | None = None
    interval: str | None = None
    horizon_candles: int | None = None
    direction: str | None = None
    prob_up: float | None = None
    prob_down: float | None = None
    prob_flat: float | None = None
    tp_before_sl_probability: float | None = None
    expected_move_atr: float | None = None
    risk_score: float | None = None
    confidence: float | None = None
    model_version: str | None = None


class ModelSummaryResponse(BaseModel):
    model_version: str
    model_name: str
    symbol: str
    interval: str
    horizon_candles: int
    feature_version: str
    label_version: str
    accuracy: float | None = None
    brier_score: float | None = None
    is_active: bool
    artifact_path: str
    created_at: str | None = None


class ModelActivateRequest(BaseModel):
    model_version: str


class ModelActivateResponse(BaseModel):
    model_version: str
    activated: bool
    warning: str | None = None


class ReplaySessionResponse(BaseModel):
    session_id: str
    model_version: str
    symbol: str
    interval: str
    start_at: str
    end_at: str
    status: str
    metrics_json: dict[str, Any] | None = None
    created_at: str | None = None
