#!venv/bin/python3
import os
import asyncio
from pathlib import Path
import logging
import orjson
import json
import websockets
import pandas as pd
from redis import asyncio as aioredis
from review import create_day_review
from config import push_uri, access_token

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
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    async with websockets.connect(target_uri) as target_websocket:
        async for message in target_websocket:
            data = orjson.loads(message)
            if data.get("type") != "review_request":
                continue
            date = data["date"]
            datasets = [
                _file for _file in log_directory.glob(f"power_*_{date}.json")
            ]
            response = {"date": date, "success": False, "type": "review"}
            if len(datasets) == 1:
                response.update(create_day_review(pd.read_json(datasets[0])))
            if len(datasets) != 0:
                await target_websocket.send(json.dumps(response))
                continue
            datasets = [
                key
                async for key in redis_connection.scan_iter(f"power:*:{date}")
            ]
            if len(datasets) != 1:
                await target_websocket.send(json.dumps(response))
                continue
            reversed_data = await redis_connection.lrange(datasets[0], 0, -1)
            if len(reversed_data) > 0:
                data = ",\n".join(reversed_data[::-1])
                df = pd.DataFrame(
                    [_row for _row in orjson.loads(f"[{data}]\n")]
                )
                response.update(create_day_review(df))
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
    uri = f"{push_uri}?token={access_token}"
    asyncio.run(main(uri))
