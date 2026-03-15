import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import Base, engine
import app.models  # noqa: F401
from app.services.feishu_stream_service import FeishuStreamService
from app.services.dingtalk_stream_service import DingTalkStreamService


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ensure tables exist. Migrations can be added later without changing service APIs.
    Base.metadata.create_all(bind=engine)

    dingtalk_stream = DingTalkStreamService()
    feishu_stream = FeishuStreamService()
    tasks: list[asyncio.Task[None]] = []

    try:
        if dingtalk_stream.enabled:
            tasks.append(asyncio.create_task(dingtalk_stream.run_forever()))
        if feishu_stream.enabled:
            tasks.append(asyncio.create_task(feishu_stream.run_forever()))
        yield
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
