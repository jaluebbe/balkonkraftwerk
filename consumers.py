import datetime
import logging
import mystrom_switch
import shelly_devices
from config import scheduled_consumers, consumers, optional_consumers

logging.basicConfig(level=logging.INFO)


def _read_device(device: dict) -> dict | None:
    if device.get("type") == "mystrom":
        return mystrom_switch.read_switch(device["host"])
    elif device.get("type") == "shelly":
        return shelly_devices.read_device(
            device["host"], device["generation"]
        )


def process_consumers_readout(report: dict) -> None:
    _today = datetime.datetime.today()
    _now = _today.strftime("%H:%M")
    _day_of_week = _today.strftime("%a")
    for _consumer in scheduled_consumers:
        _days = _consumer.get("days")
        if _days and _day_of_week not in _days:
            continue
        if (
            _consumer["from"] < _consumer["until"]
            and _consumer["from"] <= _now <= _consumer["until"]
        ) or (
            _consumer["from"] > _consumer["until"]
            and (_now >= _consumer["from"] or _now <= _consumer["until"])
        ):
            report["consumer_power"] += _consumer["power"]
            report["scheduled_consumers"].append(_consumer)
    for _consumer in consumers:
        _data = _read_device(_consumer)
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            if not _consumer.get("ignore"):
                report["consumer_power"] += _power
            report["consumers"].append(_data)
        else:
            logging.error(f"Readout of {_consumer} failed.")
    for _consumer in optional_consumers:
        _data = _read_device(_consumer)
        if _data is not None:
            _power = _data["power"]
            if not _consumer.get("ignore"):
                report["consumer_power"] += _power
            _data.update(_consumer)
            report["optional_consumers"].append(_data)
        else:
            logging.error(f"Readout of {_consumer} failed.")


def enable_consumer(consumer: dict) -> dict | None:
    if consumer.get("type") == "mystrom":
        return mystrom_switch.enable_switch(consumer["host"])
    elif consumer.get("type") == "shelly":
        return shelly_devices.enable_device(
            consumer["host"], consumer["generation"]
        )


def disable_consumer(consumer: dict) -> dict | None:
    if consumer.get("type") == "mystrom":
        return mystrom_switch.disable_switch(consumer["host"])
    elif consumer.get("type") == "shelly":
        return shelly_devices.disable_device(
            consumer["host"], consumer["generation"]
        )


def process_optional_consumers(report: dict, required_limit: float) -> float:
    for _consumer in report["optional_consumers"]:
        if required_limit > 0 and _consumer["power"] > 0:
            disable_consumer(_consumer)
            required_limit -= _consumer["power"]
        elif (
            required_limit <= 0
            and _consumer["power"] == 0
            and required_limit + _consumer["nominal_power"] < 0
        ):
            enable_consumer(_consumer)
            required_limit += _consumer["nominal_power"]
    return required_limit
