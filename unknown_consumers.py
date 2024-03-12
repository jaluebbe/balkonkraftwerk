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
    _recent_meter_power = collect_meter_power(report["utc"] - 0.5 * interval)
    if len(_recent_meter_power) > 0:
        _meter_data = json.loads(
            redis_connection.lrange("tibber_pulse", 0, 0)[0]
        )
        report["meter_consumed"] = _meter_data["lastMeterConsumption"]
        report["meter_produced"] = _meter_data["lastMeterProduction"]
        _meter_power = np.median(_recent_meter_power)
        if report.get("battery_power") is None:
            _battery_power = 0
        else:
            _battery_power = report["battery_power"]
        report["unknown_consumers_power"] = (
            _meter_power
            - report["consumer_power"]
            + report["producer_power"]
            + _battery_power
        )
    else:
        report["unknown_consumers_power"] = 0
