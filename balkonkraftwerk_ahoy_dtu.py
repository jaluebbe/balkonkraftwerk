import time
import json
import redis
import ahoy_dtu
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
            _report["required"] -= _ac_power
            _report["producer_inverters"].append(
                {
                    "id": _id,
                    "ac_power": round(_ac_power, 1),
                    "yield_total": round(_yield_total, 3),
                    "dc_voltage": round(_dc_voltage, 1),
                    "dc_current": round(_dc_current, 2),
                }
            )
        elif _data is None:
            print(f"Readout of {_id} failed.")
    _required_limit = _report["required"]
    for _id in battery_inverters:
        _new_inverter_limit = max(
            min_inverter_limit, min(max_inverter_limit, _report["required"])
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
            _report["required"] -= _ac_power
            _report["battery_inverters"].append(
                {
                    "id": _id,
                    "ac_power": round(_ac_power, 1),
                    "yield_total": round(_yield_total, 3),
                    "dc_voltage": round(_dc_voltage, 1),
                    "dc_current": round(_dc_current, 2),
                    "inverter_limit": round(_new_inverter_limit, 2),
                }
            )
        elif _data is None:
            print(f"Readout of {_id} failed.")
    _report["required"] = round(_report["required"], 1)
    print(_report)
    key = "power:{}".format(time.strftime("%Y%m%d"))
    redis_connection.lpush(key, json.dumps(_report))
    time.sleep(interval)
