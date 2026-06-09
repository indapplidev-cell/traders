from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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
    result = service.predict(request.model_dump())
    return PredictionResponse(**result)
