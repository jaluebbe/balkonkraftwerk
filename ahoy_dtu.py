import logging
import requests

ac_labels = [
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
dc_labels = ["U_DC", "I_DC", "P_DC", "YieldDay", "YieldTotal", "Irradiation"]
ac_units = ["V", "A", "W", "Hz", "", "\u00b0C", "kWh", "Wh", "W", "%", "var"]
dc_units = ["V", "A", "W", "Wh", "kWh", "%"]


def request_inverter_data(id, host="ahoy-dtu"):
    url = f"http://{host}/api/inverter/id/{id}"
    try:
        response = requests.get(url, timeout=1.1)
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        data = response.json()
        if data is None:
            logging.warning(f"Data for inverter {id} is None.")
            return
        ac_data, dc_data = data.pop("ch")
        data["ac_data"] = {
            _label: {"value": _data, "unit": _unit}
            for _label, _data, _unit in zip(ac_labels, ac_data, ac_units)
        }
        data["dc_data"] = {
            _label: {"value": _data, "unit": _unit}
            for _label, _data, _unit in zip(dc_labels, dc_data, dc_units)
        }
        return data


def set_inverter_limit(
    id, power_limit, persistent=False, absolute=True, host="ahoy-dtu"
):
    if persistent and absolute:
        cmd = "limit_persistent_absolute"
    elif persistent and not absolute:
        cmd = "limit_nonpersistent_relative"
    elif not persistent and absolute:
        cmd = "limit_nonpersistent_absolute"
    else:
        cmd = "limit_nonpersistent_relative"
    url = f"http://{host}/api/ctrl"
    try:
        response = requests.post(
            url, json={"id": id, "cmd": cmd, "val": power_limit}, timeout=1.1
        )
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()


def enable_inverter(id, host="ahoy-dtu"):
    url = f"http://{host}/api/ctrl"
    try:
        response = requests.post(
            url, json={"id": id, "cmd": cmd, "val": 1}, timeout=1.1
        )
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()


def disable_inverter(id, host="ahoy-dtu"):
    url = f"http://{host}/api/ctrl"
    try:
        response = requests.post(
            url, json={"id": id, "cmd": cmd, "val": 0}, timeout=1.1
        )
    except requests.exceptions.ConnectTimeout:
        logging.error(f"Connection to {url} timed out.")
        return
    except requests.exceptions.ReadTimeout:
        logging.error(f"Read from {url} timed out.")
        return
    if response.status_code == 200:
        return response.json()
