import datetime
import mystrom_switch
import shelly_devices
from config import *


def process_consumers(report: dict) -> None:
    _today = datetime.datetime.today()
    _now = _today.strftime("%H:%M")
    _day_of_week = _today.strftime("%a")
    for _consumer in scheduled_consumers:
        _days = _consumer.get("days")
        if _days is not None and len(_days) > 0 and _day_of_week not in _days:
            continue
        if (
            _consumer["from"] < _consumer["until"]
            and _now >= _consumer["from"]
            and _now <= _consumer["until"]
        ):
            pass
        elif _consumer["from"] > _consumer["until"] and (
            _now >= _consumer["from"] or _now <= _consumer["until"]
        ):
            pass
        else:
            continue
        report["consumer_power"] += _consumer["power"]
        report["scheduled_consumers"].append(_consumer)
    for _consumer in consumers:
        if _consumer.get("type") == "mystrom":
            _data = mystrom_switch.read_switch(_consumer["host"])
        elif _consumer.get("type") == "shelly":
            _data = shelly_devices.read_device(
                _consumer["host"], _consumer["generation"]
            )
        else:
            continue
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            report["consumer_power"] += _power
            report["consumers"].append(_data)
        else:
            print(f"Readout of {_consumer} failed.")
    for _consumer in optional_consumers:
        if _consumer.get("type") == "mystrom":
            _data = mystrom_switch.read_switch(_consumer["host"])
        elif _consumer.get("type") == "shelly":
            _data = shelly_devices.read_device(
                _consumer["host"], _consumer["generation"]
            )
        else:
            continue
        if _data is not None:
            _power = _data["power"]
            report["consumer_power"] += _power
            _data.update(_consumer)
            report["optional_consumers"].append(_data)
        else:
            print(f"Readout of {_consumer} failed.")


def enable_consumer(consumer: dict) -> dict | None:
    if consumer.get("type") == "mystrom":
        return mystrom_switch.enable_switch(consumer["host"])
    elif _consumer.get("type") == "shelly":
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
