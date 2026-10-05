"""Fetch CPI and Average Weekly Earnings from the ABS Data API (SDMX)."""

import io

import pandas as pd
import requests

from carafford.paths import AWE_RAW, CPI_RAW, STATES

BASE = "https://data.api.abs.gov.au/rest/data"
HEADERS = {"Accept": "application/vnd.sdmx.data+csv"}

# MEASURE.INDEX.TSEST.REGION.FREQ: index numbers, original, Australia + 8 capitals.
# Motor vehicles and fuel come back national only; capitals exist for all groups.
CPI_KEY = "1.10001+40080+40081.10.50+1+2+3+4+5+6+7+8.Q"
CPI_SERIES = {10001: "all_groups", 40080: "motor_vehicles", 40081: "automotive_fuel"}

# MEASURE.ESTIMATE.SEX.SECTOR.INDUSTRY.TSEST.REGION.FREQ:
# full-time adult ordinary time earnings, all sectors and industries, original
AWE_KEY = "3.1.1+2+3.7.TOT.10.AUS+1+2+3+4+5+6+7+8.S"
SEXES = {1: "Males", 2: "Females", 3: "Persons"}


def fetch(flow: str, key: str, start: str) -> pd.DataFrame:
    r = requests.get(f"{BASE}/{flow}/{key}", params={"startPeriod": start}, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def download(start: str = "2012") -> None:
    fetch("ABS,CPI,2.0.0", CPI_KEY, f"{start}-Q1").to_csv(CPI_RAW, index=False)
    fetch("ABS,AWE,1.0.0", AWE_KEY, start).to_csv(AWE_RAW, index=False)


def tidy_cpi(raw: pd.DataFrame) -> pd.DataFrame:
    q = raw["TIME_PERIOD"].str.extract(r"(?P<year>\d{4})-Q(?P<quarter>\d)").astype(int)
    out = pd.DataFrame({
        "year": q["year"],
        "quarter": q["quarter"],
        "region": raw["REGION"].astype(str).map(STATES),
        "series": raw["INDEX"].map(CPI_SERIES),
        "index": raw["OBS_VALUE"].astype(float),
    })
    return out.sort_values(["series", "region", "year", "quarter"]).reset_index(drop=True)


def tidy_awe(raw: pd.DataFrame) -> pd.DataFrame:
    h = raw["TIME_PERIOD"].str.extract(r"(?P<year>\d{4})-S(?P<half>\d)").astype(int)
    out = pd.DataFrame({
        "year": h["year"],
        "half": h["half"],
        "region": raw["REGION"].astype(str).map(STATES),
        "sex": raw["SEX"].map(SEXES),
        "weekly_ote": raw["OBS_VALUE"].astype(float),
    })
    return out.sort_values(["region", "sex", "year", "half"]).reset_index(drop=True)


def annual(df: pd.DataFrame, value: str, keys: list[str], periods: int) -> pd.DataFrame:
    """Calendar-year mean, keeping only years with every sub-period present."""
    g = df.groupby(keys + ["year"])[value].agg(["mean", "count"]).reset_index()
    return g[g["count"] == periods].drop(columns="count").rename(columns={"mean": value})
