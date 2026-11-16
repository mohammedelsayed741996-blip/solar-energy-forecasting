# Data

`solar_weather.csv.gz` is **simulated** by `src/generate_data.py` (seed 7): one reading every 15 minutes from 2017-01-01 to 2022-08-15 (197,088 rows).

| Column | Meaning |
|---|---|
| Time | Timestamp (15-minute steps) |
| Energy Captured[Wh] | Plant output in the interval (target) |
| Sun Light Intensity (W/m2) | Irradiance from the hourly weather station |
| Temperature | Air temperature, °C |
| 1 Hour Rain Fall | Rain in the last hour, mm |
| Cloud Coverage | Cloud cover, % |
| Length of Day_Light | Daylight length, minutes |

The weather columns are hourly values repeated across the four quarter-hours. The energy meter also reflects passing clouds, panel ageing (0.7% a year), soiling, snow cover and about 1.2% outage days, none of which appear in the weather columns.

Planted data-quality problems: 39 text values in numeric columns ("n/a", "--", "ERR", blanks), 6 cloud-cover values of −250 and 25 small negative energy readings at night.
