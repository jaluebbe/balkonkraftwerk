#!venv/bin/python3
from __future__ import annotations
import time
import logging
import orjson
import requests
import redis
import arrow
from config import tasmota_meter_host


def read_tasmota_meter() -> dict | None:
    url = f"http://{tasmota_meter_host}/cm"
    params = {"cmnd": "status 10"}
    try:
        response = requests.get(url, params=params, timeout=1.1)
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection to {url} failed.")
        return
    if response.status_code == 200:
        return response.json()


if __name__ == "__main__":
    redis_connection = redis.Redis()
    interval = 5
    old_time = None
    while True:
        _t_start = time.time()
        _response = read_tasmota_meter()
        if _response is None:
            time.sleep(1)
            continue
        _data = _response["StatusSNS"]
        _data["utc"] = int(_t_start)
        _data["type"] = "tasmota_meter"
        _data["lastMeterConsumption"] = _data["SML"]["1_8_0"]
        _data["lastMeterProduction"] = _data["SML"]["2_8_0"]
        _data["power"] = max(_data["SML"]["16_7_0"], 0)
        _data["powerProduction"] = -min(_data["SML"]["16_7_0"], 0)
        _data["powerL1"] = _data["SML"]["36_7_0"]
        _data["powerL2"] = _data["SML"]["56_7_0"]
        _data["powerL3"] = _data["SML"]["76_7_0"]
        if old_time != _data["Time"]:
            _json_report = orjson.dumps(_data)
            redis_connection.lpush("tibber_pulse", _json_report)
            redis_connection.ltrim("tibber_pulse", 0, 30)
            redis_connection.publish("tibber_pulse", _json_report)
            old_time = _data["Time"]
        _dt = time.time() - _t_start
        time.sleep(max(0, interval - _dt))
