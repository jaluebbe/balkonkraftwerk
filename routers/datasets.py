import json
import os
from pathlib import Path
from typing import Union
from redis import asyncio as aioredis
from fastapi import APIRouter, Query, HTTPException

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"
router = APIRouter()
log_directory = Path("../logs_json")


@router.get("/api/available_datasets")
async def get_available_datasets(
    category: str = Query("*", regex="^[*a-z0-9]*$"),
    date: str = Query("*", max_length=8, regex="^[*0-9]*$"),
):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    datasets = [
        key.replace(":", "_")
        async for key in redis_connection.scan_iter(
            f"{category}:*:{date}", count=1000
        )
    ]
    return datasets


@router.get("/api/archived_datasets")
async def get_archived_datasets(
    category: str = Query("*", regex="^[*a-z0-9]*$"),
    date: str = Query("*", max_length=8, regex="^[*0-9]*$"),
):
    datasets = [
        _file.name.rstrip(".json")
        for _file in log_directory.glob(f"{category}_*_{date}.json")
    ]
    return datasets


@router.get("/api/dataset/{_id}.json")
async def get_dataset(
    _id: str, utc_min: Union[int, None] = None, utc_max: Union[int, None] = None
):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    reversed_data = await redis_connection.lrange(_id.replace("_", ":"), 0, -1)
    if len(reversed_data) == 0:
        raise HTTPException(status_code=404, detail="dataset unknown.")
    data = ",\n".join(reversed_data[::-1])
    return [
        _row
        for _row in json.loads(f"[{data}]\n")
        if not (utc_min is not None and _row["utc"] < utc_min)
        and not (utc_max is not None and _row["utc"] > utc_max)
    ]


@router.get("/api/move_to_archive/{_id}")
async def move_to_archive(_id):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    key = _id.replace("_", ":")
    file_name = log_directory.joinpath(f"{_id}.json")
    reversed_data = await redis_connection.lrange(key, 0, -1)
    if len(reversed_data) == 0:
        raise HTTPException(status_code=404, detail="dataset unknown.")
    data = ",\n".join(reversed_data[::-1])
    json_string = f"[{data}]\n"
    if not file_name.exists():
        file_name.write_text(json_string)
    # compare to written or existing data.
    existing_data = file_name.read_text()
    if existing_data == json_string:
        # delete dataset from Redis only if a copy exists.
        await redis_connection.delete(key)
    else:
        raise HTTPException(
            status_code=409, detail="data doesn't match to existing file."
        )
    return json.loads(json_string)
