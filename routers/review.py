from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import ORJSONResponse
from config import max_inverter_limit, battery_inverter_serials

router = APIRouter()
log_directory = Path("../logs_json")
max_battery_inverter_power = max_inverter_limit * len(battery_inverter_serials)


def _energy_power(power: pd.Series, utc: pd.Series) -> float:
    return round(np.trapz(y=power.fillna(0) / 1e3, x=utc / 3600), 3)


def _plot_list(power: pd.Series) -> dict[str, list]:
    _data = power.dropna()
    return {"utc_ms": (_data.index * 1e3).to_list(), "values": _data.to_list()}


@router.get("/api/review/day", response_class=ORJSONResponse)
async def get_day_review(
    date: str = Query("*", regex="^[0-9]{8}$"),
):
    datasets = [_file for _file in log_directory.glob(f"power_*_{date}.json")]
    if len(datasets) == 0:
        raise HTTPException(status_code=404, detail="dataset unknown.")
    elif len(datasets) > 1:
        raise HTTPException(
            status_code=409, detail="no exact match for dataset."
        )
    df = pd.read_json(datasets[0]).set_index("utc")
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
    return ORJSONResponse(response)
