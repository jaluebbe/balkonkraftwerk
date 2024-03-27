import numpy as np
import pandas as pd
import arrow
from config import max_inverter_limit, battery_inverter_serials

max_battery_inverter_power = max_inverter_limit * len(battery_inverter_serials)


def _energy_power(power: pd.Series, utc: pd.Series) -> float:
    return float(round(np.trapz(y=power.fillna(0) / 1e3, x=utc / 3600), 3))


def _plot_list(power: pd.Series) -> dict[str, list]:
    _data = power.dropna()
    return {"utc_ms": (_data.index * 1e3).to_list(), "values": _data.to_list()}


def create_day_review(df: pd.DataFrame) -> dict:
    df.set_index("utc", inplace=True)
    response = {"type": "review", "success": True}
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
    response["plot_limit"] = float(max(200, df["producer_power"].max()))
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
    if "tibber_price" in df.columns:
        df_price = pd.DataFrame(
            df["tibber_price"].dropna().drop_duplicates().to_list()
        )
        df_price.dropna(inplace=True)
        if "startsAt" in df_price.columns:
            df_price["utc"] = df_price["startsAt"].apply(
                lambda x: arrow.get(x).timestamp()
            )
            df_price.set_index("utc", inplace=True)
            max_utc = df_price.index.max()
            df_price.loc[max_utc + 3599] = df_price.loc[max_utc]
            response["price"] = _plot_list(df_price["total"])
    return response
