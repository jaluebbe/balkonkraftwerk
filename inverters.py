import open_dtu
from config import *


def process_inverters_readout(report: dict) -> None:
    _inverters = open_dtu.request_inverter_data(host=open_dtu_host)
    for _serial in producer_inverter_serials + battery_inverter_serials:
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
        if not _inverter_enabled:
            pass
        elif _serial in producer_inverter_serials:
            report["producer_power"] += _ac_power
        elif _serial in battery_inverter_serials:
            report["battery_power"] += _ac_power
        _entry = {
            "serial": _serial,
            "name": _inverter["name"],
            "ac_power": round(_ac_power, 1),
            "yield_total": round(_yield_total, 3),
            "dc_voltage": round(_dc_voltage, 1),
            "dc_current": round(_dc_current, 2),
            "inverter_limit": _inverter_limit,
        }
        if _serial in producer_inverter_serials:
            report["producer_inverters"].append(_entry)
        elif _serial in battery_inverter_serials:
            _entry["enabled"] = _inverter_enabled
            report["battery_inverters"].append(_entry)


def process_inverter_limits(report: dict, required_limit: float) -> None:
    active_inverters = [
        _inverter
        for _inverter in report["battery_inverters"]
        if _inverter["enabled"]
    ]
    min_total_power = min_inverter_limit * len(active_inverters)
    for _inverter in report["battery_inverters"]:
        min_total_power -= min_inverter_limit
        _serial = _inverter["serial"]
        _battery_voltage = (
            _inverter["dc_voltage"]
            + _inverter["dc_current"] * battery_resistance
        )
        if (
            required_limit < 0
            and not _inverter["enabled"]
            or required_limit < inverter_shutdown_value
        ):
            _new_inverter_limit = 0
        elif _battery_voltage < battery_off_voltage:
            _new_inverter_limit = 0
        else:
            _new_inverter_limit = max(
                min_inverter_limit,
                min(max_inverter_limit, required_limit - min_total_power),
            )
        if _inverter["enabled"] and _new_inverter_limit == 0:
            open_dtu.disable_inverter(
                host=open_dtu_host, password=open_dtu_password, serial=_serial
            )
        elif not _inverter["enabled"] and _battery_voltage < battery_on_voltage:
            continue
        elif not _inverter["enabled"] and _new_inverter_limit > 0:
            open_dtu.enable_inverter(
                host=open_dtu_host, password=open_dtu_password, serial=_serial
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
        required_limit -= _new_inverter_limit
        _inverter["new_inverter_limit"] = round(_new_inverter_limit, 0)
