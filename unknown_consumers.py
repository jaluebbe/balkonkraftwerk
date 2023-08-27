import json
import redis
import numpy as np
from config import *

redis_connection = redis.Redis(decode_responses=True)


def collect_meter_power(utc_start: int):
    _meter_data = [
        json.loads(_row)
        for _row in redis_connection.lrange("tibber_pulse", 0, -1)[::-1]
    ]
    return [
        _row["power"] - _row["powerProduction"]
        for _row in _meter_data
        if _row["utc"] > utc_start
    ]


def process_unknown_consumers(report: dict) -> None:
    _unknown_consumers = redis_connection.get("unknown_consumers")
    if _unknown_consumers is not None:
        _unknown_consumers = json.loads(_unknown_consumers)
        utc_meter_processed = _unknown_consumers["utc"]
        if report["utc"] - _unknown_consumers["utc"] < 300:
            report["unknown_consumers_power"] = _unknown_consumers["power"]
        else:
            report["unknown_consumers_power"] = 0
    else:
        utc_meter_processed = None
    if (
        utc_meter_processed is None
        or report["utc"] - utc_meter_processed > 1.5 * interval
    ):
        _recent_meter_power = collect_meter_power(
            report["utc"] - 1.5 * interval
        )
        if len(_recent_meter_power) > 0:
            _meter_power = np.median(_recent_meter_power)
            utc_meter_processed = report["utc"]
            report["unknown_consumers_power"] = max(
                0,
                (
                    _meter_power
                    - report["consumer_power"]
                    + report["producer_power"]
                    + report["battery_power"]
                ),
            )
            redis_connection.set(
                "unknown_consumers",
                json.dumps(
                    {
                        "utc": utc_meter_processed,
                        "power": report["unknown_consumers_power"],
                    }
                ),
            )
