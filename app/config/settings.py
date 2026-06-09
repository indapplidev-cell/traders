import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class Settings(BaseModel):
    service_name: str = "traders-ml"
    service_version: str = "0.1.0"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://traders_ml:traders_ml@localhost:5433/traders_ml"


@lru_cache
def get_settings() -> Settings:
    _load_env_file(PROJECT_ROOT / ".env")
    return Settings(
        service_name=os.getenv("SERVICE_NAME", "traders-ml"),
        service_version=os.getenv("SERVICE_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "dev"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://traders_ml:traders_ml@localhost:5433/traders_ml",
        ),
    )
