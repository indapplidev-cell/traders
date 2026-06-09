from fastapi import FastAPI

from app import __version__
from app.api.routes_health import router as health_router
from app.api.routes_models import router as models_router
from app.api.routes_predict import router as predict_router
from app.api.routes_replay import router as replay_router
from app.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.service_name,
        version=__version__,
    )
    application.include_router(health_router)
    application.include_router(predict_router)
    application.include_router(models_router)
    application.include_router(replay_router)
    return application


app = create_app()
