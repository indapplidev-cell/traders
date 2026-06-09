from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ReplaySessionResponse
from app.api.routes_shared import get_replay_service
from app.db.session import db_session_dependency

router = APIRouter()


@router.get("/replay/sessions", response_model=list[ReplaySessionResponse])
def list_replay_sessions(session: Session = Depends(db_session_dependency)) -> list[ReplaySessionResponse]:
    service = get_replay_service(session)
    return [ReplaySessionResponse(**item) for item in service.list_sessions()]
