#!/usr/bin/env python3
from time import strftime
import requests

HOSTNAME = "localhost"
PORT = 8080

today = strftime("%Y%m%d")
response = requests.get(
    f"http://{HOSTNAME}:{PORT}/api/available_datasets",
    params={"category": "power"},
)
for _name in response.json():
    if _name.split("_")[-1].startswith(today):
        continue
    requests.get(f"http://{HOSTNAME}:{PORT}/api/move_to_archive/{_name}")
