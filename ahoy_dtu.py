from __future__ import annotations
import logging
import requests

AC_LABELS = [
    "U_AC",
    "I_AC",
    "P_AC",
    "F_AC",
    "PF_AC",
    "Temp",
    "YieldTotal",
    "YieldDay",
    "P_DC",
    "Efficiency",
    "Q_AC",
]
DC_LABELS = ["U_DC", "I_DC", "P_DC", "YieldDay", "YieldTotal", "Irradiation"]
AC_UNITS = ["V", "A", "W", "Hz", "", "\u00b0C", "kWh", "Wh", "W", "%", "var"]
DC_UNITS = ["V", "A", "W", "Wh", "kWh", "%"]
AHOY_HOST = "ahoy-dtu"


def _request_data(url: str) -> dict | None:
    try:
        response = requests.get(url, timeout=1.1)
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()


def _send_command(url: str, payload: dict) -> dict | None:
    try:
        response = requests.post(url, json=payload, timeout=1.1)
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()


def request_inverter_data(id: int, host: str = AHOY_HOST) -> dict | None:
    url = f"http://{host}/api/inverter/id/{id}"
    data = _request_data(url)
    if data is None:
        logging.warning(f"Data for inverter {id} is None.")
        return
    ac_data, dc_data = data.pop("ch")
    data["ac_data"] = {
        _label: {"value": _data, "unit": _unit}
        for _label, _data, _unit in zip(AC_LABELS, ac_data, AC_UNITS)
    }
    data["dc_data"] = {
        _label: {"value": _data, "unit": _unit}
        for _label, _data, _unit in zip(DC_LABELS, dc_data, DC_UNITS)
    }
    return data


def set_inverter_limit(
    id: int,
    power_limit: float,
    persistent: bool = False,
    absolute: bool = True,
    host: str = AHOY_HOST,
) -> dict | None:
    if persistent and absolute:
        cmd = "limit_persistent_absolute"
    elif persistent and not absolute:
        cmd = "limit_nonpersistent_relative"
    elif not persistent and absolute:
        cmd = "limit_nonpersistent_absolute"
    else:
        cmd = "limit_nonpersistent_relative"
    url = f"http://{host}/api/ctrl"
    payload = {"id": id, "cmd": cmd, "val": power_limit}
    return _send_command(url, payload)


def enable_inverter(id: int, host: str = AHOY_HOST) -> dict | None:
    url = f"http://{host}/api/ctrl"
    payload = {"id": id, "cmd": "power", "val": 1}
    return _send_command(url, payload)


def disable_inverter(id: int, host: str = AHOY_HOST) -> dict | None:
    url = f"http://{host}/api/ctrl"
    payload = {"id": id, "cmd": "power", "val": 0}
    return _send_command(url, payload)
