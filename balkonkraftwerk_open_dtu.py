import time
import datetime
import json
import redis
import open_dtu
import mystrom_switch
from config import *

redis_connection = redis.Redis(decode_responses=True)

while True:
    _today = datetime.datetime.today()
    _now = _today.strftime("%H:%M")
    _day_of_week = _today.strftime("%a")
    _required = min_power
    _report = {
        "utc": int(_today.timestamp()),
        "min_power": min_power,
        "consumers": [],
        "temporary_consumers": [],
        "producer_inverters": [],
        "battery_inverters": [],
    }
    for _consumer in temporary_consumers:
        _days = _consumer.get("days")
        if _days is not None and len(_days) > 0 and _day_of_week not in _days:
            continue
        if (
            _consumer["from"] < _consumer["until"]
            and _now >= _consumer["from"]
            and _now <= _consumer["until"]
        ):
            pass
        elif (
            _consumer["from"] > _consumer["until"]
            and _now >= _consumer["from"]
            or _now <= _consumer["until"]
        ):
            pass
        else:
            continue
        _required += _consumer["power"]
        _report["temporary_consumers"].append(_consumer)
    _inverters = open_dtu.request_inverter_data(host=open_dtu_host)
    for _serial in producer_inverter_serials:
        _data = _inverters.get(_serial)
        if (
            _data is not None
            and len(_data) == 1
            and _data[0]["data_age"] < inverter_timeout
        ):
            _ac_power = _data[0]["AC"]["0"]["Power"]["v"]
            _yield_total = _data[0]["AC"]["0"]["YieldTotal"]["v"]
            _dc_voltage = _data[0]["DC"]["0"]["Voltage"]["v"]
            _dc_current = _data[0]["DC"]["0"]["Current"]["v"]
            _inverter_limit = _data[0]["limit_absolute"]
            _required -= _ac_power
            _report["producer_inverters"].append(
                {
                    "ac_power": _ac_power,
                    "yield_total": _yield_total,
                    "dc_voltage": _dc_voltage,
                    "dc_current": _dc_current,
                    "inverter_limit": _inverter_limit,
                }
            )
        elif _data is None:
            print(f"Readout of {_serial} failed.")
    for _id in consumers:
        _data = mystrom_switch.read_switch(_id)
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            _required += _power
            _report["consumers"].append({"id": _id, "power": _power})
        else:
            print(f"Readout of {_id} failed.")
    _required_limit = _required
    for _serial in battery_inverter_serials:
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
        _required -= _ac_power
        _new_inverter_limit = max(
            min_inverter_limit, min(max_inverter_limit, _required)
        )
        _required_limit -= _new_inverter_limit
        _report["battery_inverters"].append(
            {
                "ac_power": _ac_power,
                "yield_total": _yield_total,
                "dc_voltage": _dc_voltage,
                "dc_current": _dc_current,
                "inverter_limit": _inverter_limit,
                "new_inverter_limit": round(_new_inverter_limit, 0),
            }
        )

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
    _report["required"] = round(_required, 2)
    key = "power:{}".format(time.strftime("%Y%m%d"))
    print(_report)
    redis_connection.lpush(key, json.dumps(_report))
    time.sleep(interval)
