import os
from pathlib import Path
import orjson
import pandas as pd
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis
from review import create_day_review

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
LOG_DIRECTORY = Path("../logs_json")

router = APIRouter()


async def get_local_review(date: str):
    datasets = [_file for _file in LOG_DIRECTORY.glob(f"power_*_{date}.json")]
    response = {"date": date, "success": False, "type": "review"}
    if len(datasets) == 1:
        response.update(create_day_review(pd.read_json(datasets[0])))
    if len(datasets) != 0:
        return response
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        datasets = [
            key async for key in redis_connection.scan_iter(f"power:*:{date}")
        ]
        if len(datasets) != 1:
            return response
        reversed_data = await redis_connection.lrange(datasets[0], 0, -1)
        if len(reversed_data) == 0:
            return response
        data = ",\n".join(reversed_data[::-1])
        df = pd.DataFrame([_row for _row in orjson.loads(f"[{data}]\n")])
        response.update(create_day_review(df))
        return response


@router.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    date: str = Query("*", regex="^[0-9]{8}$"),
):
    redis_connection = aioredis.Redis(host=REDIS_HOST, decode_responses=True)
    _key = f"power/review/day/{date}"
    json_string = await redis_connection.get(_key)
    if json_string is not None:
        return Response(content=json_string, media_type="application/json")
    _data = await get_local_review(date)
    if _data is None:
        raise HTTPException(status_code=504, detail="no response from source.")
    elif not _data["success"]:
        raise HTTPException(status_code=404, detail="no data available.")
    await redis_connection.setex(
        name=_key,
        time=900,
        value=orjson.dumps(_data, option=orjson.OPT_SERIALIZE_NUMPY),
    )
    return ORJSONResponse(_data)
