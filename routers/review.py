import os
from pathlib import Path
import orjson
import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import ORJSONResponse
from redis import asyncio as aioredis
from config import max_inverter_limit, battery_inverter_serials

if "REDIS_HOST" in os.environ:
    redis_host = os.environ["REDIS_HOST"]
else:
    redis_host = "127.0.0.1"

router = APIRouter()
log_directory = Path("../logs_json")
max_battery_inverter_power = max_inverter_limit * len(battery_inverter_serials)


def _energy_power(power: pd.Series, utc: pd.Series) -> float:
    return round(np.trapz(y=power.fillna(0) / 1e3, x=utc / 3600), 3)


def _plot_list(power: pd.Series) -> dict[str, list]:
    _data = power.dropna()
    return {"utc_ms": (_data.index * 1e3).to_list(), "values": _data.to_list()}


def create_day_review(json_file: Path) -> dict:
    df = pd.read_json(json_file).set_index("utc")
    response = {}
    response["consumer_power"] = _plot_list(df["consumer_power"])
    response["producer_power"] = _plot_list(df["producer_power"])
    response["consumer_energy"] = _energy_power(df["consumer_power"], df.index)
    response["producer_energy"] = _energy_power(df["producer_power"], df.index)
    response["unused_energy"] = _energy_power(
        np.maximum(df["producer_power"] - df["consumer_power"], 0), df.index
    )
    response["missing_energy"] = _energy_power(
        np.maximum(df["consumer_power"] - df["producer_power"], 0), df.index
    )
    response["plot_limit"] = max(200, df["producer_power"].max())
    if max_battery_inverter_power > 0:
        response["max_battery_inverter_power"] = max_battery_inverter_power
        response["battery_unreachable_energy"] = _energy_power(
            np.maximum(
                df["consumer_power"]
                - df["producer_power"]
                - max_battery_inverter_power,
                0,
            ),
            df.index,
        )
    if "battery_power" in df.columns:
        response["battery_power"] = _plot_list(df["battery_power"])
        response["battery_energy"] = _energy_power(
            df["battery_power"], df.index
        )
    return response


@router.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    date: str = Query("*", regex="^[0-9]{8}$"),
):
    redis_connection = aioredis.Redis(host=redis_host, decode_responses=True)
    _key = f"power/review/day/{date}"
    json_string = await redis_connection.get(_key)
    if json_string is not None:
        return Response(content=json_string, media_type="application/json")
    datasets = [_file for _file in log_directory.glob(f"power_*_{date}.json")]
    if len(datasets) == 0:
        raise HTTPException(status_code=404, detail="dataset unknown.")
    elif len(datasets) > 1:
        raise HTTPException(
            status_code=409, detail="no exact match for dataset."
        )
    response = create_day_review(datasets[0])
    await redis_connection.setex(
        name=_key,
        time=3600,
        value=orjson.dumps(response, option=orjson.OPT_SERIALIZE_NUMPY),
    )
    return ORJSONResponse(response)
