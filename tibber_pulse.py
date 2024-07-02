#!venv/bin/python3
import orjson
import arrow
from redis import asyncio as aioredis
import tibber
from config import tibber_api_key

account = tibber.Account(tibber_api_key)
homes = [
    _home
    for _home in account.homes
    if _home.features.real_time_consumption_enabled
]
redis_connection = aioredis.Redis()

if len(homes) > 0:
    home = homes[0]
else:
    exit(0)


@home.event("live_measurement")
async def set_and_publish_data(data):
    _data = dict(data.cache)
    _data["utc"] = int(arrow.get(_data["timestamp"]).timestamp())
    _data["utc_received"] = int(arrow.utcnow().timestamp())
    _data["type"] = "electricity_meter"
    _json_report = orjson.dumps(_data)
    await redis_connection.lpush("electricity_meter", _json_report)
    await redis_connection.ltrim("electricity_meter", 0, 30)
    await redis_connection.publish("electricity_meter", _json_report)


home.start_live_feed(user_agent="jaluebbe/balkonkraftwerk/0.0.0")
