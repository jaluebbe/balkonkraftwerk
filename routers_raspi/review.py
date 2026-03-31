import os
from pathlib import Path
from collections import defaultdict
import asyncio
import time
import orjson
import pandas as pd
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis
from review import create_day_review

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
LOG_DIRECTORY = Path("../logs_json")

router = APIRouter()

_review_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
_last_calculation: dict[str, float] = {}
CALCULATION_COOLDOWN = 900  # 15 minutes in seconds


async def get_local_review(date: str):
    async with _review_locks[date]:
        current_time = time.time()
        last_calc_time = _last_calculation.get(date, 0)
        time_since_calc = current_time - last_calc_time

        datasets = list(LOG_DIRECTORY.glob(f"review_*_{date}.json"))
        if len(datasets) == 1 and time_since_calc < CALCULATION_COOLDOWN:
            with open(datasets[0], "rb") as file:
                return orjson.loads(file.read())

        datasets = list(LOG_DIRECTORY.glob(f"power_*_{date}.json"))
        response = {"date": date, "success": False, "type": "review"}

        if len(datasets) > 1:
            return response
        elif len(datasets) == 1:
            power_file = datasets[0]
            response.update(create_day_review(pd.read_json(power_file)))
            json_response = orjson.dumps(response)
            review_file = power_file.with_name(
                power_file.name.replace("power_", "review_", 1)
            )
            with open(review_file, "wb") as file:
                file.write(json_response)
            _last_calculation[date] = current_time
            return response

        async with aioredis.Redis(
            host=REDIS_HOST, decode_responses=True
        ) as redis_connection:
            datasets = [
                key
                async for key in redis_connection.scan_iter(f"power:*:{date}")
            ]
            if len(datasets) != 1:
                return response
            reversed_data = await redis_connection.lrange(datasets[0], 0, -1)
            if len(reversed_data) == 0:
                return response
            data = ",\n".join(reversed_data[::-1])
            df = pd.DataFrame([_row for _row in orjson.loads(f"[{data}]\n")])
            response.update(create_day_review(df))
            _last_calculation[date] = current_time
            return response


@router.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    date: str = Query("*", regex="^[0-9]{8}$"),
):
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        _key = f"power/review/day/{date}"
        json_string = await redis_connection.get(_key)
        if json_string is not None:
            return Response(content=json_string, media_type="application/json")
        _data = await get_local_review(date)
        if _data is None:
            raise HTTPException(
                status_code=504, detail="no response from source."
            )
        elif not _data["success"]:
            raise HTTPException(status_code=404, detail="no data available.")
        await redis_connection.setex(
            name=_key,
            time=900,
            value=orjson.dumps(_data, option=orjson.OPT_SERIALIZE_NUMPY),
        )
    return ORJSONResponse(_data)
