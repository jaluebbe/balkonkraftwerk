import os
import time
import asyncio
import orjson
from fastapi import APIRouter, Query, HTTPException, Response, Request
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis
from routers_cloud import requires_auth

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

router = APIRouter()


async def get_review_from_channel(date: str, timeout: float = 5):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe("power_review")
    await redis_connection.publish(
        "power_review_request",
        orjson.dumps({"date": date, "type": "review_request"}),
    )
    timestamp = time.time()
    while time.time() < timestamp + timeout:
        message = await pubsub.get_message()
        if message is not None:
            _data = orjson.loads(message["data"])
            if _data.get("date") == date:
                return _data
        await asyncio.sleep(0.01)


@router.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    request: Request, date: str = Query("*", regex="^[0-9]{8}$")
):
    requires_auth(request)
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    _key = f"power/review/day/{date}"
    json_string = await redis_connection.get(_key)
    if json_string is not None:
        return Response(content=json_string, media_type="application/json")
    _data = await get_review_from_channel(date)
    if _data is None:
        raise HTTPException(status_code=504, detail="no response from source.")
    elif not _data["success"]:
        raise HTTPException(status_code=404, detail="no data available.")
    await redis_connection.setex(
        name=_key,
        time=3600,
        value=orjson.dumps(_data, option=orjson.OPT_SERIALIZE_NUMPY),
    )
    return ORJSONResponse(_data)
