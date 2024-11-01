import numpy as np
import pandas as pd
import arrow
from config import max_inverter_limit

max_battery_inverter_power = max_inverter_limit


def _energy_power(power: pd.Series, utc: pd.Series) -> float:
    return float(round(np.trapz(y=power.fillna(0) / 1e3, x=utc / 3600), 3))


def _plot_list(power: pd.Series) -> dict[str, list]:
    _data = power.dropna()
    return {"utc_ms": (_data.index * 1e3).to_list(), "values": _data.to_list()}


def create_day_review(df: pd.DataFrame) -> dict:
    df.set_index("utc", inplace=True)
    response = {"type": "review", "success": True}
    consumer_power = df["consumer_power"] + df["unknown_consumers_power"].clip(
        lower=0
    )
    producer_power = df["producer_power"]
    consumer_energy = _energy_power(consumer_power, df.index)
    producer_energy = _energy_power(producer_power, df.index)

    response["consumer_power"] = _plot_list(consumer_power)
    response["producer_power"] = _plot_list(producer_power)
    response["consumer_energy"] = consumer_energy
    response["producer_energy"] = producer_energy
    if "battery_power" in df.columns:
        battery_power = df["battery_power"]
        response["battery_power"] = _plot_list(battery_power)
        response["battery_energy"] = _energy_power(battery_power, df.index)
        combined_power = producer_power + battery_power
        response["plot_limit"] = float(max(200, combined_power.max()))
        missing_power = np.maximum(
            consumer_power - combined_power - battery_power.fillna(0), 0
        )
        response["missing_energy"] = _energy_power(missing_power, df.index)
    else:
        missing_power = np.maximum(consumer_power - producer_power, 0)
        response["missing_energy"] = _energy_power(missing_power, df.index)
        response["plot_limit"] = float(max(200, producer_power.max()))
    if "meter_consumed" in df.columns:
        _meter_consumed = df["meter_consumed"].dropna()
        response["meter_consumption_day"] = float(
            round(_meter_consumed.max() - _meter_consumed.min(), 3)
        )
        _meter_produced = df["meter_produced"].dropna()
        response["meter_production_day"] = float(
            round(_meter_produced.max() - _meter_produced.min(), 3)
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
