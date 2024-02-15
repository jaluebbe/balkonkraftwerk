#!/usr/bin/env python3
import os
import time
import logging
import asyncio
import orjson
import uvicorn
from fastapi import FastAPI, Request, WebSocket, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis

import routers.meters as meters

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(meters.router)


@app.get("/", include_in_schema=False)
async def root(request: Request):
    return RedirectResponse("/static/index.html")


async def redis_handler(websocket: WebSocket):

    async def consumer_handler(
        redis_connection: aioredis.client.Redis, websocket: WebSocket
    ):
        async for message in websocket.iter_text():
            data = orjson.loads(message)
            if data.get("type") == "tibber_pulse":
                channel = "tibber_pulse"
            elif data.get("type") == "review":
                channel = "power_review"
            else:
                channel = "balkonkraftwerk"
            await redis_connection.publish(channel, message)

    async def producer_handler(
        pubsub: aioredis.client.PubSub, websocket: WebSocket
    ):
        await pubsub.subscribe("power_review_request")
        async for message in pubsub.listen():
            await websocket.send_text(message["data"])

    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    consumer_task = asyncio.create_task(
        consumer_handler(redis_connection, websocket)
    )
    producer_task = asyncio.create_task(producer_handler(pubsub, websocket))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED
    )
    logging.debug(f"Done task: {done}")
    for task in pending:
        logging.debug(f"Cancelling task: {task}")
        task.cancel()
    await redis_connection.close()


@app.websocket("/ws/push")
async def websocket_review(websocket: WebSocket):
    await websocket.accept()
    await redis_handler(websocket)


async def get_review_from_channel(date: str, timeout: float = 5):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe("power_review")
    await redis_connection.publish(
        "power_review_request",
        orjson.dumps({"date": date, "type": "review_request"}),
    )
    timestamp = time.time()
    while time.time() < timestamp + timeout:
        message = await pubsub.get_message()
        if message is not None:
            _data = orjson.loads(message["data"])
            if _data.get("date") == date:
                return _data
        await asyncio.sleep(0.01)


@app.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    date: str = Query("*", regex="^[0-9]{8}$"),
):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    _key = f"power/review/day/{date}"
    json_string = await redis_connection.get(_key)
    if json_string is not None:
        return Response(content=json_string, media_type="application/json")
    _data = await get_review_from_channel(date)
    if _data is None:
        raise HTTPException(status_code=404, detail="dataset not available.")
    await redis_connection.setex(
        name=_key,
        time=3600,
        value=orjson.dumps(_data, option=orjson.OPT_SERIALIZE_NUMPY),
    )
    return ORJSONResponse(_data)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
