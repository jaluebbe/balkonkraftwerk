from __future__ import annotations
import logging
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


def read_switch(host: str) -> dict | None:
    url = f"http://{host}/report"
    result = _perform_request(url)
    if result is not None:
        result["id"] = host
        return result


def enable_switch(host: str) -> dict | None:
    url = f"http://{host}/relay?state=1"
    return _perform_request(url)


def disable_switch(host: str) -> dict | None:
    url = f"http://{host}/relay?state=1"
    return _perform_request(url)
