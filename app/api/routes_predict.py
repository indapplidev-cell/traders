from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.gate_policy_response_builder import (
    build_gate_policy_api_block_from_prediction_payload,
)
from app.api.schemas import PredictionRequest, PredictionResponse
from app.api.routes_shared import get_prediction_service
from app.db.session import db_session_dependency

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
def predict(
    request: PredictionRequest,
    session: Session = Depends(db_session_dependency),
) -> PredictionResponse:
    service = get_prediction_service(session)
    request_payload = request.model_dump()
    result = service.predict(request_payload)
    response_payload = {
        **result,
        "gate_policy": build_gate_policy_api_block_from_prediction_payload(
            result,
            request_payload=request_payload,
        ),
    }
    return PredictionResponse(**response_payload)
