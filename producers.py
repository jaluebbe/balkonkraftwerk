import logging
import mystrom_switch
import shelly_devices
from config import producers, battery_producers

logging.basicConfig(level=logging.INFO)


def _process_producer(producer: dict, report: dict) -> dict | None:
    if producer.get("type") == "mystrom":
        return mystrom_switch.read_switch(producer["host"])
    elif producer.get("type") == "shelly":
        return shelly_devices.read_device(
            producer["host"], producer["generation"]
        )


def process_producers(report: dict) -> None:
    for _producer in producers:
        _data = _process_producer(_producer, report)
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            report["producer_power"] += _power
            report["producers"].append(_data)
        else:
            logging.error(f"Readout of {_producer} failed.")
    for _producer in battery_producers:
        report.setdefault("battery_power", 0)
        report.setdefault("battery_producers", [])
        _data = _process_producer(_producer, report)
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            report["battery_power"] += _power
            report["battery_producers"].append(_data)
        else:
            logging.error(f"Readout of {_producer} failed.")
