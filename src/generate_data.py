"""Generate the simulated solar plant + weather dataset used in this repository.

The data imitates a small photovoltaic installation in central Europe (latitude ~52°N),
one reading every 15 minutes from 2017-01-01 to 2022-08-15. Weather comes from an hourly
station; energy comes from the plant's own meter and also reflects passing clouds,
panel ageing, soiling, snow cover and occasional outages that the weather columns
do not show. A few data-quality problems are
planted on purpose (text in numeric cells, impossible values, gaps) so the cleaning
steps in the notebook have something real to do.

Run:  python src/generate_data.py      -> writes data/solar_weather.csv.gz
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 7
LAT = np.radians(52.0)
OUT = Path(__file__).resolve().parents[1] / "data" / "solar_weather.csv.gz"


def main():
    rng = np.random.default_rng(SEED)
    t = pd.date_range("2017-01-01", "2022-08-15 23:45", freq="15min")
    n = len(t)
    doy = t.dayofyear.values
    hour = t.hour.values + t.minute.values / 60

    # Sun position and length of daylight (minutes)
    decl = np.radians(23.44) * np.sin(2 * np.pi * (284 + doy) / 365)
    hour_angle = np.radians(15 * (hour - 12))
    sin_elev = np.sin(LAT) * np.sin(decl) + np.cos(LAT) * np.cos(decl) * np.cos(hour_angle)
    sin_elev = np.clip(sin_elev, 0, None)
    day_len = 2 * np.degrees(np.arccos(np.clip(-np.tan(LAT) * np.tan(decl), -1, 1))) / 15 * 60

    # Cloud cover: slowly varying random process, cloudier in winter
    shocks = rng.normal(0, 1, n)
    ar = np.empty(n)
    ar[0] = 0
    for i in range(1, n):
        ar[i] = 0.995 * ar[i - 1] + 0.1 * shocks[i]
    season = np.cos(2 * np.pi * (doy - 15) / 365)  # +1 mid-winter, -1 mid-summer
    cloud = 100 / (1 + np.exp(-(ar * 1.6 + 0.6 * season + 0.4)))
    cloud = np.clip(cloud + rng.normal(0, 4, n), 0, 100)

    # Irradiance (W/m2): clear-sky scaled by cloud attenuation
    clear_sky = 290 * sin_elev ** 1.15
    sun = clear_sky * (1 - 0.72 * (cloud / 100) ** 2.2) * rng.normal(1, 0.05, n)
    sun = np.clip(sun, 0, None)

    # Temperature (°C): seasonal + daily cycle + sun warming + noise
    temp = (9.5 - 9 * season + 4 * np.sin(2 * np.pi * (hour - 9) / 24) + 0.012 * sun
            + np.cumsum(rng.normal(0, 0.05, n)) * 0.02 + rng.normal(0, 1.2, n))

    # Rain (mm in the last hour): only under heavy cloud
    rain = np.where((cloud > 75) & (rng.random(n) < 0.12), rng.gamma(0.8, 0.6, n), 0.0)

    # The plant sees its own irradiance; the weather columns come from an hourly station
    # nearby. Passing clouds make plant irradiance fluctuate within the hour, more so on
    # partly cloudy days.
    partly = 4 * (cloud / 100) * (1 - cloud / 100)          # 0 when clear or overcast, 1 at 50%
    plant_sun = sun * np.exp(rng.normal(0, 0.05 + 0.35 * partly, n))

    # Energy (Wh per 15 min): plant irradiance x efficiency, with real-world losses
    years = (t - t[0]).days.values / 365.25
    efficiency = (1 - 0.004 * np.clip(temp - 25, 0, None)) * (1 - 0.007 * years)   # heat + ageing
    soiling = 1 - 0.06 * ((doy % 45) / 45)                                          # dirt, cleaned every ~45 days
    day = t.normalize()
    day_ids, day_idx = np.unique(day, return_inverse=True)
    outage = (rng.random(len(day_ids)) < 0.012)[day_idx]                            # inverter / grid downtime
    snow_day = (pd.Series(temp, index=t).groupby(day).transform("min").values < -1.5) & \
               (rng.random(len(day_ids)) < 0.5)[day_idx]
    energy = plant_sun * 17.5 * efficiency * soiling * rng.normal(1, 0.04, n)
    energy = np.where(snow_day, energy * 0.25, energy)
    energy = np.where(outage | (sun < 0.5), 0, energy)
    energy = np.round(np.clip(energy, 0, 5020))                                     # inverter limit

    # Hourly weather station: every quarter-hour inside an hour repeats the hourly value
    hourly = pd.DataFrame({"sun": sun, "temp": temp, "cloud": cloud, "rain": rain}, index=t)
    hourly = hourly.groupby(t.floor("h")).transform("mean")
    sun, temp, cloud, rain = (hourly[c].values for c in ["sun", "temp", "cloud", "rain"])

    df = pd.DataFrame({
        "Time": t,
        "Energy Captured[Wh]": energy,
        "Sun Light Intensity (W/m2)": np.round(sun, 1),
        "Temperature": np.round(temp, 1),
        "1 Hour Rain Fall": np.round(rain, 2),
        "Cloud Coverage": np.round(cloud).astype(int),
        "Length of Day_Light": np.round(day_len).astype(int),
    })

    # Planted data-quality problems
    df = df.astype({c: object for c in df.columns if c != "Time"})
    for col, k in [("Energy Captured[Wh]", 4), ("Sun Light Intensity (W/m2)", 7), ("Temperature", 6),
                   ("1 Hour Rain Fall", 4), ("Cloud Coverage", 13), ("Length of Day_Light", 5)]:
        idx = rng.choice(n, k, replace=False)
        df.loc[idx, col] = rng.choice(["n/a", "--", "ERR", ""], k)
    df.loc[rng.choice(n, 6, replace=False), "Cloud Coverage"] = -250
    night = np.flatnonzero(energy == 0)
    df.loc[rng.choice(night, 25, replace=False), "Energy Captured[Wh]"] = -rng.integers(1, 55, 25)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, compression="gzip")
    print(f"Wrote {OUT} ({len(df):,} rows)")


if __name__ == "__main__":
    main()
