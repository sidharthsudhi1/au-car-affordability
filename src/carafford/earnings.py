"""Reshape the ABS Employee Earnings data cube (Data 1) into tidy long format."""

import pandas as pd

from carafford.paths import STATE_NAMES

ID_COLS = ["parameter", "sex", "work_status", "leave", "survey_month"]


def read_cube(path) -> pd.DataFrame:
    head = pd.read_csv(path, skiprows=5, nrows=1, header=None).iloc[0]
    states = head.ffill().iloc[5:].tolist()
    kinds = ["value" if i % 2 == 0 else "rse" for i in range(len(states))]

    body = pd.read_csv(path, skiprows=7, header=None, dtype=str)
    body.columns = ID_COLS + [f"{s}|{k}" for s, k in zip(states, kinds, strict=True)]
    body = body.dropna(subset=["survey_month"])
    body = body[body["parameter"].str.contains("earnings|Employees", na=False)]

    long = body.melt(id_vars=ID_COLS, var_name="col", value_name="raw")
    long[["state", "kind"]] = long["col"].str.split("|", expand=True)
    long["raw"] = pd.to_numeric(long["raw"].str.replace(",", ""), errors="coerce")
    wide = long.pivot_table(index=ID_COLS + ["state"], columns="kind", values="raw", aggfunc="first")
    wide = wide.reset_index()
    wide.columns.name = None

    wide["state"] = wide["state"].map(STATE_NAMES)
    wide["sex"] = wide["sex"].str.strip()
    wide["year"] = 2000 + wide["survey_month"].str[-2:].astype(int)
    wide.loc[wide["year"] > 2050, "year"] -= 100
    # The cube pads unpublished early years with 0.0 rather than leaving them blank
    wide.loc[wide["value"] == 0, ["value", "rse"]] = pd.NA
    return wide.drop(columns="survey_month").dropna(subset=["value"])


def median_weekly(cube: pd.DataFrame, since: int = 2014) -> pd.DataFrame:
    m = cube[(cube["parameter"] == "Median weekly earnings") & (cube["year"] >= since)]
    out = m[["year", "state", "sex", "work_status", "leave", "value", "rse"]]
    out = out.rename(columns={"value": "median_weekly", "rse": "rse_pct"})
    # ABS convention: RSE 25-50% use with caution, above 50% too unreliable for general use
    out["reliability"] = pd.cut(out["rse_pct"], [-1, 25, 50, 1000], labels=["ok", "caution", "unreliable"])
    return out.sort_values(["state", "sex", "work_status", "leave", "year"]).reset_index(drop=True)
