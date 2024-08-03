import datetime
import mystrom_switch
import shelly_devices
from config import producers


def process_producers(report: dict) -> None:
    for _producer in producers:
        if _producer.get("type") == "mystrom":
            _data = mystrom_switch.read_switch(_producer["host"])
        elif _producer.get("type") == "shelly":
            _data = shelly_devices.read_device(
                _producer["host"], _producer["generation"]
            )
        else:
            continue
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            report["producer_power"] += _power
            report["producers"].append(_data)
        else:
            print(f"Readout of {_producer} failed.")
