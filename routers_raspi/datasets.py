from __future__ import annotations
import os
from pathlib import Path
import orjson
from redis import asyncio as aioredis
from fastapi import APIRouter, Query, HTTPException, Response

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
LOG_DIRECTORY = Path("../logs_json")

router = APIRouter()


@router.get("/api/available_datasets")
async def get_available_datasets(
    category: str = Query("*", regex="^[*a-z0-9]*$"),
    date: str = Query("*", max_length=8, regex="^[*0-9]*$"),
) -> list[str]:
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
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
) -> list[str]:
    datasets = [
        _file.name.rstrip(".json")
        for _file in LOG_DIRECTORY.glob(f"{category}_*_{date}.json")
    ]
    return datasets


@router.get("/api/dataset/{_id}.json")
async def get_dataset(
    _id: str, utc_min: int | None = None, utc_max: int | None = None
) -> list[dict]:
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        reversed_data = await redis_connection.lrange(
            _id.replace("_", ":"), 0, -1
        )
        if len(reversed_data) == 0:
            raise HTTPException(status_code=404, detail="dataset unknown.")
        data = ",\n".join(reversed_data[::-1])
        return [
            _row
            for _row in orjson.loads(f"[{data}]\n")
            if not (utc_min is not None and _row["utc"] < utc_min)
            and not (utc_max is not None and _row["utc"] > utc_max)
        ]


@router.get("/api/move_to_archive/{_id}")
async def move_to_archive(_id: str):
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        key = _id.replace("_", ":")
        file_name = LOG_DIRECTORY.joinpath(f"{_id}.json")
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
        return Response(content=json_string, media_type="application/json")
