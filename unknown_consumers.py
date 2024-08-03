import json
import redis
import numpy as np
from config import unknown_consumers_interval

redis_connection = redis.Redis(decode_responses=True)


def collect_meter_power(utc_start: int, key: str = "electricity_meter"):
    _meter_data = [
        json.loads(_row) for _row in redis_connection.lrange(key, 0, -1)[::-1]
    ]
    return [
        _row["power"] - _row["powerProduction"]
        for _row in _meter_data
        if _row["utc"] > utc_start
    ]


def process_unknown_consumers(report: dict) -> None:
    _recent_electricity_meter_power = collect_meter_power(
        report["utc"] - unknown_consumers_interval, "electricity_meter"
    )
    _recent_smart_meter_power = collect_meter_power(
        report["utc"] - unknown_consumers_interval, "smart_meter"
    )
    # ensure that recent consumption data is available
    if len(_recent_electricity_meter_power) > 0:
        _meter_data = json.loads(
            redis_connection.lrange("electricity_meter", 0, 0)[0]
        )
        report["meter_consumed"] = _meter_data["lastMeterConsumption"]
        report["meter_produced"] = _meter_data["lastMeterProduction"]
    # prefer smart meter data over electricity meter readout
    if len(_recent_smart_meter_power) > 0:
        _meter_power = np.median(_recent_smart_meter_power)
    elif len(_recent_electricity_meter_power) > 0:
        _meter_power = np.median(_recent_electricity_meter_power)
    else:
        report["unknown_consumers_power"] = 0
        return
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
