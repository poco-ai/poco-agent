import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for database connections."""
    # Startup
    logger.info("Starting application...")
    logger.info("Database engine initialized")
    yield
    # Shutdown
    logger.info("Shutting down database engine...")
    engine.dispose()
    logger.info("Database engine disposed")
