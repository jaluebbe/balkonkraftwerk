#!/usr/bin/env python3
import json
import arrow
from redis import asyncio as aioredis
import tibber

account = tibber.Account("-AD5Ahxgk-u7NEQpPWg3_14XCCBBPcQDwWezs7J4QNY")
home = account.homes[0]
redis_connection = aioredis.Redis()


@home.event("live_measurement")
async def set_and_publish_data(data):
    _data = dict(data.cache)
    _data["utc"] = int(arrow.get(_data["timestamp"]).timestamp())
    _data["utc_received"] = int(arrow.utcnow().timestamp())
    _json_report = json.dumps(_data)
    await redis_connection.lpush("tibber_pulse", _json_report)
    await redis_connection.ltrim("tibber_pulse", 0, 30)
    await redis_connection.publish("tibber_pulse", _json_report)


home.start_live_feed(user_agent="jaluebbe/balkonkraftwerk/0.0.0")
