from __future__ import annotations
import logging
import requests


def _request_data(url: str) -> dict | None:
    try:
        response = requests.get(url, timeout=1.1)
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error for {url}.")
        return
    if response.status_code == 200:
        return response.json()


def _send_command(url: str, password: str, payload: dict) -> dict | None:
    try:
        response = requests.post(
            url, auth=("admin", password), json=payload, timeout=1.1
        )
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()


def request_inverter_data(host: str, serial: str = None) -> list | None:
    url = f"http://192.168.12.91/api/livedata/status"
    data = _request_data(url)
    if data is None:
        logging.warning("Open DTU data is None.")
        return
    inverters = data.get("inverters")
    if inverters is None:
        logging.warning("No data for inverters available.")
        return
    if serial is None:
        return inverters
    else:
        return [
            _inverter
            for _inverter in inverters
            if _inverter["serial"] == serial
        ]


def set_inverter_limit(
    host: str,
    password: str,
    serial: str,
    power_limit: float,
    persistent: bool = False,
    absolute: bool = True,
) -> dict | None:
    if persistent and absolute:
        limit_type = 256
    elif persistent and not absolute:
        limit_type = 257
    elif not persistent and absolute:
        limit_type = 0
    else:
        limit_type = 1
    url = f"http://{host}/api/limit/config"
    payload = {
        "serial": serial,
        "limit_type": limit_type,
        "limit_value": power_limit,
    }
    return _send_command(url, password, payload)


def enable_inverter(host: str, password: str, serial: str) -> dict | None:
    url = f"http://{host}/api/power/config"
    payload = {"serial": serial, "power": True}
    return _send_command(url, password, payload)


def disable_inverter(host: str, password: str, serial: str) -> dict | None:
    url = f"http://{host}/api/power/config"
    payload = {"serial": serial, "power": False}
    return _send_command(url, password, payload)


def restart_inverter(host: str, password: str, serial: str) -> dict | None:
    url = f"http://{host}/api/power/config"
    payload = {"serial": serial, "restart": True}
    return _send_command(url, password, payload)
