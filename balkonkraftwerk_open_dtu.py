import time
import json
import redis
import open_dtu
import mystrom_switch
from consumers import process_consumers
from config import *

redis_connection = redis.Redis(decode_responses=True)

while True:
    _report = {
        "utc": int(time.time()),
        "min_power": min_power,
        "consumers": [],
        "scheduled_consumers": [],
        "producer_inverters": [],
        "battery_inverters": [],
        "required": min_power,
    }
    process_consumers(_report)
    _inverters = open_dtu.request_inverter_data(host=open_dtu_host)
    for _serial in producer_inverter_serials:
        _inverter = _inverters.get(_serial)
        if _inverter is None:
            print(f"Readout of {_serial} failed.")
            continue
        if _inverter["data_age"] > inverter_timeout:
            print(f"Data of {_serial} is too old.")
            continue
        _ac_power = _inverter["AC"]["0"]["Power"]["v"]
        _yield_total = _inverter["AC"]["0"]["YieldTotal"]["v"]
        _dc_voltage = _inverter["DC"]["0"]["Voltage"]["v"]
        _dc_current = _inverter["DC"]["0"]["Current"]["v"]
        _inverter_limit = _inverter["limit_absolute"]
        _report["required"] -= _ac_power
        _report["producer_inverters"].append(
            {
                "ac_power": round(_ac_power, 1),
                "yield_total": round(_yield_total, 3),
                "dc_voltage": round(_dc_voltage, 1),
                "dc_current": round(_dc_current, 2),
                "inverter_limit": _inverter_limit,
            }
        )
    _required_limit = _report["required"]
    for _serial in battery_inverter_serials:
        _new_inverter_limit = max(
            min_inverter_limit, min(max_inverter_limit, _report["required"])
        )
        _required_limit -= _new_inverter_limit
        _inverter = _inverters.get(_serial)
        if _inverter is None:
            print(f"Readout of {_serial} failed.")
            continue
        if _inverter["data_age"] > inverter_timeout:
            print(f"Data of {_serial} is too old.")
            continue
        _ac_power = _inverter["AC"]["0"]["Power"]["v"]
        _yield_total = _inverter["AC"]["0"]["YieldTotal"]["v"]
        _dc_voltage = _inverter["DC"]["0"]["Voltage"]["v"]
        _dc_current = _inverter["DC"]["0"]["Current"]["v"]
        _inverter_limit = _inverter["limit_absolute"]
        _report["required"] -= _ac_power
        _report["battery_inverters"].append(
            {
                "ac_power": round(_ac_power, 1),
                "yield_total": round(_yield_total, 3),
                "dc_voltage": round(_dc_voltage, 1),
                "dc_current": round(_dc_current, 2),
                "inverter_limit": _inverter_limit,
                "new_inverter_limit": round(_new_inverter_limit, 0),
            }
        )
        if abs(_inverter_limit - _new_inverter_limit) > limit_tolerance:
            _response = open_dtu.set_inverter_limit(
                host=open_dtu_host,
                password=open_dtu_password,
                serial=_serial,
                power_limit=_new_inverter_limit,
            )
            if _response is None:
                print(
                    f"Problem setting the inverter limit of {_new_inverter_limit}W."
                )
    _report["required"] = round(_report["required"], 1)
    print(_report)
    key = "power:{}".format(time.strftime("%Y%m%d"))
    redis_connection.lpush(key, json.dumps(_report))
    time.sleep(interval)
