import datetime
import mystrom_switch
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
    for _id in consumers:
        _data = mystrom_switch.read_switch(_id)
        if _data is not None:
            _power = _data["power"]
            if _power == 0:
                continue
            report["consumer_power"] += _power
            report["consumers"].append({"id": _id, "power": _power})
        else:
            print(f"Readout of {_id} failed.")
