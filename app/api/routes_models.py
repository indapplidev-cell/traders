from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import ModelActivateRequest, ModelActivateResponse, ModelSummaryResponse
from app.api.routes_shared import get_model_registry
from app.db.session import db_session_dependency

router = APIRouter()


@router.get("/models", response_model=list[ModelSummaryResponse])
def list_models(session: Session = Depends(db_session_dependency)) -> list[ModelSummaryResponse]:
    registry = get_model_registry(session)
    return [ModelSummaryResponse(**item) for item in registry.list_models()]


@router.post("/models/activate", response_model=ModelActivateResponse)
def activate_model(
    request: ModelActivateRequest,
    session: Session = Depends(db_session_dependency),
) -> ModelActivateResponse:
    registry = get_model_registry(session)
    try:
        result = registry.activate(request.model_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ModelActivateResponse(**result)
