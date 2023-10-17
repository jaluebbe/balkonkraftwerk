from __future__ import annotations
import logging
import requests


def read_devices(host: str, generation: int = 1) -> dict | None:
    if generation == 1:
        url = f"http://{host}/status"
    elif generation == 2:
        url = f"http://{host}/rpc/Switch.GetStatus?id=0"
    else:
        logging.error(f"Unknown generation {generation} set for {host}.")
        return
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
        data = response.json()
        if generation == 2:
            data["power"] = data["apower"]
        else:
            data = data["meters"][0]
        return data
