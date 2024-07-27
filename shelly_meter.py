#!venv/bin/python3
import time
import orjson
from config import shelly_3em_host
from shelly_devices import read_device


if __name__ == "__main__":
    redis_connection = redis.Redis()
    interval = 5
    old_time = None
    while True:
        _t_start = time.time()
        _response = read_device(shelly_3em_host)
        if _response is None:
            time.sleep(1)
            continue
        _data = {}
        _data["utc"] = _response["utc"]
        _data["type"] = "smart_meter"
        _data["power"] = max(_response["power"], 0)
        _data["powerProduction"] = -min(_response["power"], 0)
        _data["powerL1"] = _response["L1"]["power"]
        _data["powerL2"] = _response["L2"]["power"]
        _data["powerL3"] = _response["L3"]["power"]
        _data["currentL1"] = _response["L1"]["current"]
        _data["currentL2"] = _response["L2"]["current"]
        _data["currentL3"] = _response["L3"]["current"]
        _data["voltagePhase1"] = _response["L1"]["voltage"]
        _data["voltagePhase2"] = _response["L2"]["voltage"]
        _data["voltagePhase3"] = _response["L3"]["voltage"]
        if old_time != _data["utc"]:
            _json_report = orjson.dumps(_data)
            redis_connection.lpush("smart_meter", _json_report)
            redis_connection.ltrim("smart_meter", 0, 30)
            redis_connection.publish("smart_meter", _json_report)
            old_time = _data["utc"]
        _dt = time.time() - _t_start
        time.sleep(max(0, interval - _dt))
