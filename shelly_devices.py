from __future__ import annotations
import logging
import time
import requests


def _perform_request(url) -> dict | None:
    try:
        response = requests.get(url, timeout=1.1)
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection to {url} failed.")
        return
    if response.status_code == 200:
        return response.json()


def _filter_emeter(data: dict) -> dict | None:
    if not data["is_valid"]:
        return
    return {
        _key: _value
        for _key, _value in data.items()
        if _key in ("power", "current", "voltage")
    }


def _read_device_gen2_3em(host: str) -> dict | None:
    em_response = _perform_request(f"http://{host}/rpc/EM.GetStatus?id=0")
    if em_response is None:
        return None
    return {
        "id": host,
        "utc": int(time.time()),
        "power": em_response["total_act_power"],
        "L1": {
            "power": em_response["a_act_power"],
            "current": em_response["a_current"],
            "voltage": em_response["a_voltage"],
        },
        "L2": {
            "power": em_response["b_act_power"],
            "current": em_response["b_current"],
            "voltage": em_response["b_voltage"],
        },
        "L3": {
            "power": em_response.get(
                "c_active_power", em_response.get("c_act_power")
            ),
            "current": em_response["c_current"],
            "voltage": em_response["c_voltage"],
        },
    }


def read_device(host: str, generation: int | str = 1) -> dict | None:
    if generation == "2_3em":
        return _read_device_gen2_3em(host)
    elif generation == 1:
        url = f"http://{host}/status"
    elif generation == 2:
        url = f"http://{host}/rpc/Switch.GetStatus?id=0"
    else:
        logging.error(f"Unknown generation {generation} set for {host}.")
        return
    response = _perform_request(url)
    if response is not None:
        if generation == 2:
            data = {
                "id": host,
                "power": response["apower"],
                "relay": response["output"],
                "temperature": response["temperature"]["tC"],
            }
        else:
            data = {
                "id": host,
                "utc": response["unixtime"],
            }
            if response.get("meters") is not None:
                data["power"] = response["meters"][0]["power"]
            elif response.get("emeters") is not None:
                data["power"] = response["total_power"]
                data["L1"] = _filter_emeter(response["emeters"][0])
                data["L2"] = _filter_emeter(response["emeters"][1])
                data["L3"] = _filter_emeter(response["emeters"][2])
            if response.get("relays") is not None:
                data["relay"] = response["relays"][0]["ison"]
            if response.get("temperature") is not None:
                data["temperature"] = response["temperature"]
        return data


def enable_device(host: str, generation: int = 1) -> dict | None:
    if generation == 1:
        url = f"http://{host}/relay/0?turn=on"
    elif generation == 2:
        url = f"http://{host}/rpc/Switch.Set?id=0&on=true"
    else:
        logging.error(f"Unknown generation {generation} set for {host}.")
        return
    return _perform_request(url)


def disable_device(host: str, generation: int = 1) -> dict | None:
    if generation == 1:
        url = f"http://{host}/relay/0?turn=off"
    elif generation == 2:
        url = f"http://{host}/rpc/Switch.Set?id=0&on=false"
    else:
        logging.error(f"Unknown generation {generation} set for {host}.")
        return
    return _perform_request(url)
