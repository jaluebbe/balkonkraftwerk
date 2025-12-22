#!venv/bin/python3
import os
import asyncio
from pathlib import Path
from collections import defaultdict
import time
import logging
import orjson
import websockets
import pandas as pd
from redis import asyncio as aioredis
from review import create_day_review
from config import push_uri, access_token

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
LOG_DIRECTORY = Path("../logs_json")

_review_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_last_calculation: dict[str, float] = {}
CALCULATION_COOLDOWN = 900  # 15 minutes in seconds


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

                async with _review_locks[date]:
                    current_time = time.time()
                    last_calc_time = _last_calculation.get(date, 0)
                    time_since_calc = current_time - last_calc_time

                    datasets = list(LOG_DIRECTORY.glob(f"review_*_{date}.json"))
                    if (
                        len(datasets) == 1
                        and time_since_calc < CALCULATION_COOLDOWN
                    ):
                        logging.info(
                            f"Serving cached review for {date} "
                            f"(calculated {int(time_since_calc)}s ago)"
                        )
                        with open(datasets[0], "rb") as file:
                            await target_websocket.send(file.read())
                        continue

                    datasets = list(LOG_DIRECTORY.glob(f"power_*_{date}.json"))
                    response = {
                        "date": date,
                        "success": False,
                        "type": "review",
                    }

                    if len(datasets) == 1:
                        logging.info(
                            f"Calculating review from power file for {date} "
                            f"(last calc {int(time_since_calc)}s ago)"
                        )
                        power_file = datasets[0]
                        response.update(
                            create_day_review(pd.read_json(power_file))
                        )
                        json_response = orjson.dumps(response)
                        await target_websocket.send(json_response)
                        review_file = power_file.with_name(
                            power_file.name.replace("power_", "review_", 1)
                        )
                        with open(review_file, "wb") as file:
                            file.write(json_response)
                        _last_calculation[date] = current_time
                        continue
                    elif len(datasets) > 1:
                        logging.warning(
                            f"Multiple power files found for {date}"
                        )
                        await target_websocket.send(orjson.dumps(response))
                        continue

                    datasets = [
                        key
                        async for key in redis_connection.scan_iter(
                            f"power:*:{date}"
                        )
                    ]
                    if len(datasets) != 1:
                        logging.debug(f"No data found in Redis for {date}")
                        await target_websocket.send(orjson.dumps(response))
                        continue

                    logging.info(
                        f"Calculating review from Redis data for {date} "
                        f"(last calc {int(time_since_calc)}s ago)"
                    )
                    reversed_data = await redis_connection.lrange(
                        datasets[0], 0, -1
                    )
                    if len(reversed_data) > 0:
                        data = ",\n".join(reversed_data[::-1])
                        df = pd.DataFrame(
                            [_row for _row in orjson.loads(f"[{data}]\n")]
                        )
                        response.update(create_day_review(df))
                        _last_calculation[date] = current_time
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
