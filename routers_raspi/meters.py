import os
from redis import asyncio as aioredis
from fastapi import APIRouter, WebSocket, status

router = APIRouter()

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, channel: str | None = None):
    supported_channels = ["balkonkraftwerk", "electricity_meter", "smart_meter"]
    await websocket.accept()
    if channel is not None and channel not in supported_channels:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
        if channel is None:
            await pubsub.subscribe(*supported_channels)
        else:
            await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            await websocket.send_text(message["data"])
