#!/usr/bin/env python3
import os
import logging
import asyncio
import httpx
import orjson
import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi import HTTPException
from redis import asyncio as aioredis
from starlette.middleware.sessions import SessionMiddleware

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


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/")


@app.get("/", include_in_schema=False)
async def root(request: Request):
    return RedirectResponse("/static/index.html")


async def redis_handler(websocket: WebSocket, email: str):
    async def consumer_handler(
        redis_connection: aioredis.client.Redis, websocket: WebSocket
    ):
        async for message in websocket.iter_text():
            data = orjson.loads(message)
            if data.get("type") == "tibber_pulse":
                channel = f"tibber_pulse:{email}"
            elif data.get("type") == "review":
                channel = f"power_review:{email}"
            else:
                channel = f"balkonkraftwerk:{email}"
            await redis_connection.publish(channel, message)

    async def producer_handler(
        pubsub: aioredis.client.PubSub, websocket: WebSocket
    ):
        await pubsub.subscribe(f"power_review_request:{email}")
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


async def validate_token(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        response = await client.get(
            "https://api.github.com/user/emails", headers=headers
        )
    email = [
        _item["email"] for _item in response.json() if _item["primary"] == True
    ][0]
    return email


@app.websocket("/ws/push")
async def websocket_review(websocket: WebSocket, token: str):
    email = await validate_token(token)
    await websocket.accept()
    await redis_handler(websocket, email)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
