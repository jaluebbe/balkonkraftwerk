#!venv/bin/python3
import os
import asyncio
from pathlib import Path
import logging
import orjson
import json
import websockets
from redis import asyncio as aioredis
from review import create_day_review
from config import push_uri

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

log_directory = Path("../logs_json")


async def push_data(target_uri: str):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe("balkonkraftwerk", "tibber_pulse")
    async with websockets.connect(target_uri) as target_websocket:
        async for message in pubsub.listen():
            await target_websocket.send(message["data"])
    await redis_connection.close()


async def serve_reviews(target_uri: str):
    async with websockets.connect(target_uri) as target_websocket:
        async for message in target_websocket:
            data = orjson.loads(message)
            if data.get("type") != "review_request":
                continue
            date = data["date"]
            datasets = [
                _file for _file in log_directory.glob(f"power_*_{date}.json")
            ]
            if len(datasets) != 1:
                continue
            response = create_day_review(datasets[0])
            response["date"] = date
            await target_websocket.send(json.dumps(response))
    await redis_connection.close()


async def main(target_uri: str):
    push_data_task = asyncio.create_task(push_data(target_uri))
    serve_reviews_task = asyncio.create_task(serve_reviews(target_uri))
    done, pending = await asyncio.wait(
        [push_data_task, serve_reviews_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    logging.debug(f"Done task: {done}")
    for task in pending:
        logging.debug(f"Cancelling task: {task}")
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main(push_uri))
