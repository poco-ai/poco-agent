import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import Base, engine
import app.models  # noqa: F401
from app.services.poller_service import PollerService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ensure tables exist. Migrations can be added later without changing service APIs.
    Base.metadata.create_all(bind=engine)

    poller = PollerService()
    tasks: list[asyncio.Task[None]] = []

    try:
        tasks.append(asyncio.create_task(poller.run_user_input_loop()))
        tasks.append(asyncio.create_task(poller.run_sessions_recent_loop()))
        tasks.append(asyncio.create_task(poller.run_sessions_full_loop()))
        yield
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
