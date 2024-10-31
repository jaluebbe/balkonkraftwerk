import os
import time
import asyncio
import orjson
from fastapi import APIRouter, Query, HTTPException, Response, Request
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")

router = APIRouter()


def extract_email(request: Request):
    email = request.session.get("user")
    if not email:
        raise HTTPException(status_code=401, detail="unidentified user")
    return email


async def get_review_from_channel(
    date: str, email: str, timeout: float = 10
) -> dict | None:
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        pubsub = redis_connection.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(f"power_review:{email}")
        await redis_connection.publish(
            f"power_review_request:{email}",
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
    email = extract_email(request)
    async with aioredis.Redis(
        host=REDIS_HOST, decode_responses=True
    ) as redis_connection:
        _key = f"power/review/day/{date}:{email}"
        json_string = await redis_connection.get(_key)
        if json_string is not None:
            return Response(content=json_string, media_type="application/json")
        _data = await get_review_from_channel(date, email)
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
