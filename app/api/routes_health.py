from fastapi import APIRouter

from app import __version__
from app.api.schemas import HealthResponse
from app.config.settings import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=__version__,
    )
