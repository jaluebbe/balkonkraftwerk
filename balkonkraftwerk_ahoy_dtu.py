import time
import datetime
import json
import redis
import ahoy_dtu
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
        elif _consumer["from"] > _consumer["until"] and (
            _now >= _consumer["from"] or _now <= _consumer["until"]
        ):
            pass
        else:
            continue
        _required += _consumer["power"]
        _report["temporary_consumers"].append(_consumer)
    for _id in producer_inverters:
        _data = ahoy_dtu.request_inverter_data(_id, host=ahoy_dtu_host)
        if (
            _data is not None
            and time.time() - _data["ts_last_success"] < inverter_timeout
        ):
            _ac_power = _data["ac_data"]["P_AC"]["value"]
            _yield_total = _data["ac_data"]["YieldTotal"]["value"]
            _dc_voltage = _data["dc_data"]["U_DC"]["value"]
            _dc_current = _data["dc_data"]["I_DC"]["value"]
            _required -= _ac_power
            _report["producer_inverters"].append(
                {
                    "ac_power": _ac_power,
                    "yield_total": _yield_total,
                    "dc_voltage": _dc_voltage,
                    "dc_current": _dc_current,
                }
            )
        elif _data is None:
            print(f"Readout of {_id} failed.")
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
    for _id in battery_inverters:
        _new_inverter_limit = max(
            min_inverter_limit, min(max_inverter_limit, _required)
        )
        _required_limit -= _new_inverter_limit
        if (
            ahoy_dtu.set_inverter_limit(
                _id, _new_inverter_limit, host=ahoy_dtu_host
            )
            is None
        ):
            print(
                f"Problem setting the inverter limit of {_new_inverter_limit}W."
            )
        _data = ahoy_dtu.request_inverter_data(_id, host=ahoy_dtu_host)
        if (
            _data is not None
            and time.time() - _data["ts_last_success"] < inverter_timeout
        ):
            _ac_power = _data["ac_data"]["P_AC"]["value"]
            _yield_total = _data["ac_data"]["YieldTotal"]["value"]
            _dc_voltage = _data["dc_data"]["U_DC"]["value"]
            _dc_current = _data["dc_data"]["I_DC"]["value"]
            _required -= _ac_power
            _report["battery_inverters"].append(
                {
                    "ac_power": _ac_power,
                    "yield_total": _yield_total,
                    "dc_voltage": _dc_voltage,
                    "dc_current": _dc_current,
                    "inverter_limit": round(_new_inverter_limit, 2),
                }
            )
        elif _data is None:
            print(f"Readout of {_id} failed.")
    _report["required"] = round(_required, 2)
    key = "power:{}".format(time.strftime("%Y%m%d"))
    print(_report)
    redis_connection.lpush(key, json.dumps(_report))
    time.sleep(interval)
