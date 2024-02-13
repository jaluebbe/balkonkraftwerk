import os
from pathlib import Path
import orjson
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis
from review import create_day_review

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

log_directory = Path("../logs_json")

router = APIRouter()


@router.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    date: str = Query("*", regex="^[0-9]{8}$"),
):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    _key = f"power/review/day/{date}"
    json_string = await redis_connection.get(_key)
    if json_string is not None:
        return Response(content=json_string, media_type="application/json")
    datasets = [_file for _file in log_directory.glob(f"power_*_{date}.json")]
    if len(datasets) == 0:
        raise HTTPException(status_code=404, detail="dataset unknown.")
    elif len(datasets) > 1:
        raise HTTPException(
            status_code=409, detail="no exact match for dataset."
        )
    response = create_day_review(datasets[0])
    await redis_connection.setex(
        name=_key,
        time=3600,
        value=orjson.dumps(response, option=orjson.OPT_SERIALIZE_NUMPY),
    )
    return ORJSONResponse(response)
