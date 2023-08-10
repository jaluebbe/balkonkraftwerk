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
        if not _inverter["reachable"]:
            continue
        _ac_power = _inverter["AC"]["0"]["Power"]["v"]
        _yield_total = _inverter["AC"]["0"]["YieldTotal"]["v"]
        _dc_voltage = _inverter["DC"]["0"]["Voltage"]["v"]
        _dc_current = _inverter["DC"]["0"]["Current"]["v"]
        _inverter_limit = _inverter["limit_absolute"]
        _report["required"] -= _ac_power
        _report["producer_inverters"].append(
            {
                "serial": _serial,
                "name": _inverter["name"],
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
            0, min(max_inverter_limit, _report["required"])
        )
        _required_limit -= _new_inverter_limit
        _inverter = _inverters.get(_serial)
        if _inverter is None:
            print(f"Readout of {_serial} failed.")
            continue
        if not _inverter["reachable"]:
            continue
        _ac_power = _inverter["AC"]["0"]["Power"]["v"]
        _yield_total = _inverter["AC"]["0"]["YieldTotal"]["v"]
        _dc_voltage = _inverter["DC"]["0"]["Voltage"]["v"]
        _dc_current = _inverter["DC"]["0"]["Current"]["v"]
        _inverter_limit = _inverter["limit_absolute"]
        _inverter_enabled = _inverter["producing"]
        _report["required"] -= _ac_power
        _report["battery_inverters"].append(
            {
                "serial": _serial,
                "name": _inverter["name"],
                "ac_power": round(_ac_power, 1),
                "yield_total": round(_yield_total, 3),
                "dc_voltage": round(_dc_voltage, 1),
                "dc_current": round(_dc_current, 2),
                "inverter_limit": _inverter_limit,
                "enabled": _inverter_enabled,
                "new_inverter_limit": round(_new_inverter_limit, 0),
            }
        )
        if _inverter_enabled and _new_inverter_limit == 0:
            open_dtu.disable_inverter(
                host=open_dtu_host, password=open_dtu_password, serial=_serial
            )
            continue
        elif not _inverter_enabled and _new_inverter_limit > 0:
            open_dtu.enable_inverter(
                host=open_dtu_host, password=open_dtu_password, serial=_serial
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
    _key = "power:{}".format(time.strftime("%Y%m%d"))
    _json_report = json.dumps(_report)
    redis_connection.lpush(_key, _json_report)
    redis_connection.publish("balkonkraftwerk", _json_report)
    time.sleep(interval)
