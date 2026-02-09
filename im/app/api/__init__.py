from fastapi import FastAPI

from app.api.v1 import api_v1_router


def setup_routers(app: FastAPI) -> None:
    """Registers all API routers."""
    app.include_router(api_v1_router, prefix="/api/v1")
