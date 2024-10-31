#!venv/bin/python3
import os
import asyncio
from pathlib import Path
import logging
import orjson
import websockets
import pandas as pd
from redis import asyncio as aioredis
from review import create_day_review
from config import push_uri, access_token

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
LOG_DIRECTORY = Path("../logs_json")


async def push_data(target_uri: str):
    async with aioredis.Redis(host=REDIS_HOST) as redis_connection:
        pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(
            "balkonkraftwerk", "electricity_meter", "smart_meter"
        )
        async with websockets.connect(target_uri) as target_websocket:
            async for message in pubsub.listen():
                await target_websocket.send(message["data"])


async def serve_reviews(target_uri: str):
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        async with websockets.connect(target_uri) as target_websocket:
            async for message in target_websocket:
                data = orjson.loads(message)
                if data.get("type") != "review_request":
                    continue
                logging.debug(f"review request received: {data}")
                date = data["date"]
                datasets = list(LOG_DIRECTORY.glob(f"review_*_{date}.json"))
                if len(datasets) == 1:
                    with open(datasets[0], "rb") as file:
                        await target_websocket.send(file.read())
                    continue
                datasets = list(LOG_DIRECTORY.glob(f"power_*_{date}.json"))
                response = {"date": date, "success": False, "type": "review"}
                if len(datasets) == 1:
                    power_file = datasets[0]
                    response.update(create_day_review(pd.read_json(power_file)))
                    json_response = orjson.dumps(response)
                    await target_websocket.send(json_response)
                    review_file = power_file.with_name(
                        power_file.name.replace("power_", "review_", 1)
                    )
                    with open(review_file, "wb") as file:
                        file.write(json_response)
                    continue
                elif len(datasets) > 1:
                    await target_websocket.send(orjson.dumps(response))
                    continue
                datasets = [
                    key
                    async for key in redis_connection.scan_iter(
                        f"power:*:{date}"
                    )
                ]
                if len(datasets) != 1:
                    await target_websocket.send(orjson.dumps(response))
                    continue
                reversed_data = await redis_connection.lrange(
                    datasets[0], 0, -1
                )
                if len(reversed_data) > 0:
                    data = ",\n".join(reversed_data[::-1])
                    df = pd.DataFrame(
                        [_row for _row in orjson.loads(f"[{data}]\n")]
                    )
                    response.update(create_day_review(df))
                await target_websocket.send(orjson.dumps(response))


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
