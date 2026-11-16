"""Checks that the simulated solar data keeps its planted problems and known physics."""
from pathlib import Path

import pandas as pd
import pytest

DATA = Path(__file__).resolve().parents[1] / "data" / "solar_weather.csv.gz"
TARGET = "Energy Captured[Wh]"
NUMERIC = [TARGET, "Sun Light Intensity (W/m2)", "Temperature", "1 Hour Rain Fall", "Cloud Coverage",
           "Length of Day_Light"]


@pytest.fixture(scope="module")
def raw():
    return pd.read_csv(DATA, keep_default_na=False, low_memory=False)


@pytest.fixture(scope="module")
def clean(raw):
    d = raw.copy()
    d["Time"] = pd.to_datetime(d["Time"])
    for c in NUMERIC:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def test_regular_15_minute_series(clean):
    assert len(clean) == 197088
    assert clean["Time"].is_unique
    assert (clean["Time"].diff().dropna() == pd.Timedelta("15min")).all()


def test_planted_text_values_are_present(raw, clean):
    expected = {TARGET: 4, "Sun Light Intensity (W/m2)": 7, "Temperature": 6, "1 Hour Rain Fall": 4,
                "Cloud Coverage": 13, "Length of Day_Light": 5}
    for col, n in expected.items():
        assert clean[col].isna().sum() == n, col


def test_planted_impossible_values(clean):
    assert (clean["Cloud Coverage"] < 0).sum() == 6
    assert (clean[TARGET] < 0).sum() == 25


def test_no_energy_at_night_and_summer_beats_winter(clean):
    d = clean.dropna(subset=[TARGET])
    night = d[d["Time"].dt.hour.isin([0, 1, 2, 23])]
    assert (night[TARGET] <= 0).all()
    by_month = d.groupby(d["Time"].dt.month)[TARGET].mean()
    assert by_month[6] > 5 * by_month[12]
