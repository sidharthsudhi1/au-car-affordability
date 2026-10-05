"""Clean the Kaggle Australian Vehicle Prices listings (2023 snapshot)."""

import re

import numpy as np
import pandas as pd

SNAPSHOT_YEAR = 2023
MIN_PRICE, MAX_PRICE = 2_000, 400_000
MAX_KM = 500_000
MAX_AGE = 20
MAX_NEW_KM = 5_000

SPLIT_BRANDS = {"Land": "Land Rover", "Alfa": "Alfa Romeo", "Aston": "Aston Martin", "Great": "Great Wall"}
BRAND_ALIASES = {"Great Wall": "GWM", "Ssangyong": "SsangYong"}
BODY_TYPES = {"Ute / Tray": "Ute", "People Mover": "People Mover", "Other": None}
STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"}
PLACEHOLDERS = {"-", "- / -", "POA", ""}


class Funnel:
    """Records rows kept at each cleaning step so the pipeline is auditable."""

    def __init__(self):
        self.steps = []

    def log(self, step: str, df: pd.DataFrame) -> pd.DataFrame:
        prev = self.steps[-1]["rows"] if self.steps else len(df)
        self.steps.append({"step": step, "rows": len(df), "dropped": prev - len(df)})
        return df

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.steps)


def first_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.extract(r"(\d+(?:\.\d+)?)")[0], errors="coerce")


def fix_split_brands(df: pd.DataFrame) -> pd.DataFrame:
    split = df["brand"].isin(SPLIT_BRANDS)
    df.loc[split, "brand"] = df.loc[split, "brand"].map(SPLIT_BRANDS)
    # Two-word brands pushed their second word into Model; recover model from the title
    df.loc[split, "model"] = df.loc[split, "title"].str.split().str[3]
    df["brand"] = df["brand"].replace(BRAND_ALIASES)
    return df


def fix_shifted_seats(df: pd.DataFrame) -> pd.DataFrame:
    shifted = df["doors"].str.contains("Seats", na=False)
    df.loc[shifted & df["seats"].isna(), "seats"] = df.loc[shifted, "doors"]
    df.loc[shifted, "doors"] = pd.NA
    return df


def parse(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=lambda c: re.sub(r"(?<!^)(?=[A-Z])", "_", c.replace("/", "_")).lower())
    df = df.rename(columns={"car__suv": "listing_label", "used_or_new": "condition",
                            "cylindersin_engine": "cylinders_raw", "colour_ext_int": "colour"})
    for c in df.select_dtypes(include=["object", "string"]).columns:
        df[c] = df[c].str.strip().replace(dict.fromkeys(PLACEHOLDERS, pd.NA))

    df = fix_split_brands(df)
    df = fix_shifted_seats(df)

    engine = df["engine"].astype("string")
    out = pd.DataFrame({
        "brand": df["brand"],
        "model": df["model"],
        "title": df["title"],
        "year": pd.to_numeric(df["year"], errors="coerce").astype("Int64"),
        "condition": df["condition"].str.title(),
        "body_type": df["body_type"].replace(BODY_TYPES),
        "transmission": df["transmission"],
        "drive_type": df["drive_type"],
        "fuel_type": df["fuel_type"],
        "engine_litres": pd.to_numeric(engine.str.extract(r"([\d.]+)\s*L")[0], errors="coerce"),
        "cylinders": pd.to_numeric(engine.str.extract(r"(\d+)\s*cyl")[0], errors="coerce").astype("Int64"),
        "fuel_l_100km": first_number(df["fuel_consumption"]),
        "km": pd.to_numeric(df["kilometres"], errors="coerce"),
        "doors": first_number(df["doors"]).astype("Int64"),
        "seats": first_number(df["seats"]).astype("Int64"),
        "state": df["location"].str.extract(r",\s*([A-Z]{2,3})$")[0],
        "price": pd.to_numeric(df["price"], errors="coerce"),
    })
    out.loc[~out["state"].isin(STATES), "state"] = pd.NA
    out.loc[out["fuel_type"].eq("Electric"), "cylinders"] = 0
    out["age"] = SNAPSHOT_YEAR - out["year"]
    return out


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = Funnel()
    f.log("raw listings", raw)
    df = f.log("drop blank rows", raw.dropna(how="all"))
    df = parse(df)
    df = f.log("drop missing or POA price", df.dropna(subset=["price"]))
    df = f.log("drop near-duplicate listings", df.drop_duplicates(subset=["title", "price", "km", "state"]))
    df = f.log(f"keep price ${MIN_PRICE:,} to ${MAX_PRICE:,}", df[df["price"].between(MIN_PRICE, MAX_PRICE)])
    df = f.log(f"keep age 0 to {MAX_AGE} years", df[df["age"].between(0, MAX_AGE)])
    df = f.log(f"drop km above {MAX_KM:,}", df[~(df["km"] > MAX_KM)])
    inconsistent = df["condition"].eq("New") & (df["km"] > MAX_NEW_KM)
    df = f.log(f"drop 'new' cars with over {MAX_NEW_KM:,} km", df[~inconsistent])
    df = f.log("drop unknown body type", df.dropna(subset=["body_type"]))
    df = df.reset_index(drop=True)
    df["log_price"] = np.log(df["price"])
    return df, f.frame()
