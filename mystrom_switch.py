from __future__ import annotations
import logging
import requests


def read_switch(host: str) -> dict | None:
    url = f"http://{host}/report"
    try:
        response = requests.get(url)
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection to {url} failed.")
        return
    if response.status_code == 200:
        return response.json()
