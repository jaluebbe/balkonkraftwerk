from __future__ import annotations
import logging
import requests


def _request_data(url: str) -> dict | None:
    try:
        response = requests.get(url, timeout=3.1)
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
            url,
            auth=("admin", password),
            data=payload,
            timeout=3.1,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()


def request_inverter_data(host: str) -> dict:
    url = f"http://{host}/api/livedata/status"
    data = _request_data(url)
    if data is None:
        logging.warning("Open DTU data is None.")
        return {}
    inverters = data.get("inverters")
    if inverters is None:
        logging.warning("No data for inverters available.")
        return {}
    return {_inverter["serial"]: _inverter for _inverter in inverters}


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
    payload = (
        f'data={{"serial":"{serial}", "limit_type":{limit_type}, '
        f'"limit_value":{power_limit:.0f}}}'
    )
    return _send_command(url, password, payload)


def enable_inverter(host: str, password: str, serial: str) -> dict | None:
    url = f"http://{host}/api/power/config"
    payload = f'data={{"serial":"{serial}", "power":true}}'
    return _send_command(url, password, payload)


def disable_inverter(host: str, password: str, serial: str) -> dict | None:
    url = f"http://{host}/api/power/config"
    payload = f'data={{"serial":"{serial}", "power":false}}'
    return _send_command(url, password, payload)


def restart_inverter(host: str, password: str, serial: str) -> dict | None:
    url = f"http://{host}/api/power/config"
    payload = f'data={{"serial":"{serial}", "restart":true}}'
    return _send_command(url, password, payload)
