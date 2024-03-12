#!venv/bin/python3
import time
import orjson
import socket
import redis
import numpy as np
import open_dtu
import mystrom_switch
from consumers import process_consumers
from producers import process_producers
from inverters import process_inverters_readout, process_inverter_limits
from newmove_one import read_newmove_one
from unknown_consumers import process_unknown_consumers
from tibber_price import tibber_price
from config import *

redis_connection = redis.Redis(decode_responses=True)
hostname = socket.gethostname()
if tibber_api_key is not None:
    tp = tibber_price(tibber_api_key)

while True:
    _report = {
        "utc": int(time.time()),
        "min_power": min_power,
        "consumers": [],
        "producers": [],
        "scheduled_consumers": [],
        "producer_inverters": [],
        "battery_inverters": [],
        "consumer_power": min_power,
        "producer_power": 0,
        "unknown_consumers_power": 0,
    }

    # read out newmove one if available
    if newmove_one_host is not None:
        _report["newmove_one"] = read_newmove_one(newmove_one_host)
    process_consumers(_report)
    process_producers(_report)
    process_inverters_readout(_report)
    process_unknown_consumers(_report)
    _required_limit = _report["consumer_power"] - _report["producer_power"]
    if consider_unknown_consumers:
        _required_limit += max(
            0, _report["unknown_consumers_power"] - unknown_consumers_offset
        )
    if _report.get("battery_power") is not None:
        _report["required"] = round(
            _required_limit - _report["battery_power"], 1
        )
    else:
        _report["required"] = round(_required_limit, 1)
    process_inverter_limits(_report, _required_limit)
    for _key in [
        "consumer_power",
        "producer_power",
        "battery_power",
        "unknown_consumers_power",
    ]:
        if _report.get(_key) is not None:
            _report[_key] = round(_report[_key], 1)
    _key = "power:{}:{}".format(hostname, time.strftime("%Y%m%d"))
    if tibber_api_key is not None:
        _report["tibber_price"] = tp.get_price()
    _json_report = orjson.dumps(_report, option=orjson.OPT_SERIALIZE_NUMPY)
    redis_connection.set("required_power", _report["required"])
    redis_connection.lpush(_key, _json_report)
    redis_connection.publish("balkonkraftwerk", _json_report)
    time.sleep(interval)
