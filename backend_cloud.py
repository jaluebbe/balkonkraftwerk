#!/usr/bin/env python3
import os
import logging
import asyncio
import orjson
import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
from redis import asyncio as aioredis
from starlette.middleware.sessions import SessionMiddleware

from routers_cloud import requires_auth
import routers_cloud.review as review
import routers_cloud.meters as meters
import routers_cloud.github_auth as github_auth

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(meters.router)
app.include_router(review.router)
app.include_router(github_auth.router)

secret_key = os.environ["SECRET_KEY"]
app.add_middleware(SessionMiddleware, secret_key=secret_key, https_only=True)


@app.get("/login-test")
async def login_test(request: Request):
    requires_auth(request)
    user = request.session.get("user")
    return user


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/")


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
