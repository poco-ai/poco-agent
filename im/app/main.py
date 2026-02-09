import logging

from fastapi import FastAPI

from app.api import setup_routers
from app.core.errors.exception_handlers import setup_exception_handlers
from app.core.lifespan import lifespan
from app.core.middleware import setup_middleware
from app.core.observability.logging import configure_logging
from app.core.settings import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        debug=settings.debug,
        service_name="im",
        access_log=settings.uvicorn_access_log,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    setup_middleware(app)
    setup_exception_handlers(app, debug=settings.debug)
    setup_routers(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
