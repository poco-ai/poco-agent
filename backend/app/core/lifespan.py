import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from app.core.database import engine
from app.services.im_event_dispatcher import ImEventDispatcher
from app.core.settings import get_settings
from app.im.services.dingtalk_stream_service import DingTalkStreamService
from app.im.services.feishu_stream_service import FeishuStreamService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for database connections."""
    _ = app
    logger.info("Starting application...")
    logger.info("Database engine initialized")

    settings = get_settings()
    if settings.bootstrap_on_startup:
        from app.init_data.bootstrap import DataBootstrapService

        await run_in_threadpool(DataBootstrapService.bootstrap_all)
        logger.info("Built-in data bootstrap completed")

    dispatcher = ImEventDispatcher()
    dingtalk_stream = DingTalkStreamService()
    feishu_stream = FeishuStreamService()
    tasks: list[asyncio.Task[None]] = []

    try:
        if dispatcher.enabled:
            tasks.append(asyncio.create_task(dispatcher.run_forever()))
        if dingtalk_stream.enabled:
            tasks.append(asyncio.create_task(dingtalk_stream.run_forever()))
        if feishu_stream.enabled:
            tasks.append(asyncio.create_task(feishu_stream.run_forever()))
        yield
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Shutting down database engine...")
        engine.dispose()
        logger.info("Database engine disposed")
