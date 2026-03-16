import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from app.core.database import engine
from app.core.settings import get_settings
from app.services.im_streams import DingTalkStreamService
from app.services.im_streams import FeishuStreamService
from app.lifecycle.bootstrap import LifecycleBootstrapService
from app.services.im import ImEventDispatcher

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown tasks."""
    _ = app
    logger.info("Starting application...")
    logger.info("Database engine initialized")

    settings = get_settings()
    if settings.bootstrap_on_startup:
        await run_in_threadpool(LifecycleBootstrapService.bootstrap_all)
        logger.info("Lifecycle bootstrap completed")

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
