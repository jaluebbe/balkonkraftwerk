import os
from typing import Annotated
from redis import asyncio as aioredis
from fastapi import APIRouter, WebSocket, status
from starlette.websockets import WebSocketDisconnect

router = APIRouter()

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, channel: str | None = None):
    user = websocket.session.get("user")
    supported_channels = ["balkonkraftwerk", "tibber_pulse"]
    await websocket.accept()
    if not user:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="unidentified user"
        )
        return
    if channel is not None and channel not in supported_channels:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    if channel is None:
        target_channels = (
            f"{_channel}:{user}" for _channel in supported_channels
        )
        await pubsub.subscribe(*target_channels)
    else:
        await pubsub.subscribe(f"{channel}:{user}")
    async for message in pubsub.listen():
        try:
            await websocket.send_text(message["data"])
        except WebSocketDisconnect:
            break
    await redis_connection.close()
