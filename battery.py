from config import (
    charger_reference,
    battery_resistance,
    battery_full_voltage,
    battery_on_voltage,
    battery_off_voltage,
    max_inverter_limit,
)


def _get_charger_reference_inverter(report: dict) -> dict | None:
    _inverters = [
        _inverter
        for _inverter in report["producer_inverters"]
        if _inverter["serial"] == charger_reference["serial"]
    ]
    if len(_inverters) != 1:
        return
    _inverter = _inverters[0]
    if not "power" in _inverter and "ac_power" in _inverter:
        _inverter["power"] = _inverter.pop("ac_power")
    return _inverter


def _get_charger_reference_producer(report: dict) -> dict | None:
    _producers = [
        _producer
        for _producer in report["producers"]
        if _producer["id"] == charger_reference["host"]
    ]
    if len(_producers) != 1:
        return
    return _producers[0]


def get_battery_status(report: dict) -> dict:
    _inverter = report["battery_inverter"]
    _battery_voltage = (
        _inverter["dc_voltage"] + _inverter["dc_current"] * battery_resistance
    )
    _response = {
        "voltage": _battery_voltage,
        "ok": _battery_voltage > battery_on_voltage,
        "low": _battery_voltage < battery_off_voltage,
        "full": (
            _battery_voltage > battery_full_voltage
            if battery_full_voltage is not None
            else False
        ),
    }
    _reference = None
    if charger_reference.get("type") == "producer_inverter":
        _reference = _get_charger_reference_inverter(report)
    elif charger_reference.get("type") == "producer":
        _reference = _get_charger_reference_producer(report)
    _charger_power = (
        _reference["power"] * charger_reference["factor"] if _reference else 0
    )
    _response["charger_power"] = _charger_power
    _response["available_power"] = min(
        max(_charger_power - report["battery_power"], 0),
        max_inverter_limit,
    )
    return _response
