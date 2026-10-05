"""Affordability measures, hedonic price model and mix-shift decomposition.

Run: python -m carafford.analysis  (writes data/clean/analysis/*.csv)
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from carafford.paths import CLEAN, INTERIM

OUT = CLEAN / "analysis"
SNAPSHOT_YEAR = 2023
BASE_YEAR = 2014
SEGMENTS = ["Hatchback", "Sedan", "SUV", "Ute", "Wagon"]
TOP_BRANDS = 15
Z95 = 1.96
SEED = 5147

HEDONIC = (
    "log_price ~ age + I(age**2) + log_km + C(body_type, Treatment('Hatchback'))"
    " + C(brand_g, Treatment('Toyota')) + C(state, Treatment('NSW'))"
    " + C(fuel_type) + C(transmission) + C(drive_type)"
)


def load_listings() -> pd.DataFrame:
    df = pd.read_csv(INTERIM / "listings_clean.csv")
    df["log_km"] = np.log1p(df["km"])
    top = df["brand"].value_counts().index[:TOP_BRANDS]
    df["brand_g"] = df["brand"].where(df["brand"].isin(top), "Other")
    df["is_new"] = df["condition"].isin(["New", "Demo"])
    return df


def model_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(subset=["log_km", "state", "fuel_type", "transmission", "drive_type"])


# --- Price of a typical new car, anchored to listings and moved through time by the CPI ---


def typical_new_price(df: pd.DataFrame) -> float:
    return float(df.loc[df["is_new"], "price"].median())


def car_price_series(cpi_annual: pd.DataFrame, anchor_price: float) -> pd.DataFrame:
    """Back-cast the 2023 anchor price with the quality-adjusted motor vehicles index."""
    aus = cpi_annual[cpi_annual["region"] == "AUS"].pivot(index="year", columns="series", values="index")
    s = pd.DataFrame(index=aus.index)
    s["motor_vehicles_index"] = aus["motor_vehicles"]
    s["all_groups_index"] = aus["all_groups"]
    s["car_price"] = anchor_price * aus["motor_vehicles"] / aus.loc[SNAPSHOT_YEAR, "motor_vehicles"]
    s["real_car_index"] = (aus["motor_vehicles"] / aus["all_groups"]) / (
        aus.loc[BASE_YEAR, "motor_vehicles"] / aus.loc[BASE_YEAR, "all_groups"]
    )
    return s.reset_index()


def weeks_by_awe(prices: pd.DataFrame, awe_annual: pd.DataFrame) -> pd.DataFrame:
    """Weeks of full-time adult ordinary time earnings needed to buy the typical new car."""
    out = awe_annual.merge(prices[["year", "car_price"]], on="year")
    out["weeks"] = out["car_price"] / out["weekly_ote"]
    base = out[out["year"] == BASE_YEAR].set_index(["region", "sex"])["weeks"]
    out["weeks_vs_2014"] = out["weeks"] / out.set_index(["region", "sex"]).index.map(base)
    return out[out["year"] >= BASE_YEAR].sort_values(["region", "sex", "year"]).reset_index(drop=True)


def weeks_by_group(prices: pd.DataFrame, earnings: pd.DataFrame) -> pd.DataFrame:
    """Weeks of median earnings by sex x work status, with a 95% CI from the ABS RSE."""
    g = earnings[(earnings["state"] == "AUS") & (earnings["leave"] == "Total")]
    g = g.merge(prices[["year", "car_price"]], on="year")
    se = g["median_weekly"] * g["rse_pct"] / 100
    g["weeks"] = g["car_price"] / g["median_weekly"]
    # Inverting the earnings interval: higher earnings means fewer weeks
    g["weeks_lo"] = g["car_price"] / (g["median_weekly"] + Z95 * se)
    g["weeks_hi"] = g["car_price"] / (g["median_weekly"] - Z95 * se)
    cols = ["year", "sex", "work_status", "median_weekly", "rse_pct", "car_price",
            "weeks", "weeks_lo", "weeks_hi"]
    return g[cols].sort_values(["sex", "work_status", "year"]).reset_index(drop=True)


# --- 2023 market structure from listings ---


def bootstrap_median(x: np.ndarray, n_boot: int = 2000, rng=None) -> tuple[float, float, float]:
    rng = rng or np.random.default_rng(SEED)
    draws = rng.choice(x, size=(n_boot, len(x)), replace=True)
    meds = np.median(draws, axis=1)
    return float(np.median(x)), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def new_segment_prices(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for seg in SEGMENTS:
        x = df.loc[df["is_new"] & (df["body_type"] == seg), "price"].to_numpy()
        med, lo, hi = bootstrap_median(x, rng=rng)
        rows.append({"segment": seg, "n": len(x), "median_price": med, "ci_lo": lo, "ci_hi": hi})
    return pd.DataFrame(rows)


def group_segment_matrix(seg_prices: pd.DataFrame, earnings: pd.DataFrame) -> pd.DataFrame:
    """Weeks of 2023 median earnings to buy the median new car in each segment."""
    g = earnings[(earnings["state"] == "AUS") & (earnings["leave"] == "Total")
                 & (earnings["year"] == SNAPSHOT_YEAR)]
    g = g[g["sex"].isin(["Males", "Females"]) & g["work_status"].isin(["Full-time", "Part-time"])]
    m = g.merge(seg_prices, how="cross")
    m["group"] = m["work_status"] + " " + m["sex"].str.lower()
    m["weeks"] = m["median_price"] / m["median_weekly"]
    m["weeks_lo"] = m["ci_lo"] / m["median_weekly"]
    m["weeks_hi"] = m["ci_hi"] / m["median_weekly"]
    return m[["group", "sex", "work_status", "median_weekly", "segment", "median_price",
              "weeks", "weeks_lo", "weeks_hi"]]


def fit_hedonic(df: pd.DataFrame):
    return smf.ols(HEDONIC, data=model_frame(df)).fit(cov_type="HC3")


def cross_validate(df: pd.DataFrame, folds: int = 5) -> pd.DataFrame:
    """Out-of-sample error of the hedonic model against a segment-median baseline."""
    d = model_frame(df).reset_index(drop=True)
    rows = []
    fold_of = np.random.default_rng(SEED).permutation(len(d)) % folds
    for k in range(folds):
        train, test = d[fold_of != k], d[fold_of == k]
        pred = smf.ols(HEDONIC, data=train).fit().predict(test)
        base = test["body_type"].map(train.groupby("body_type")["log_price"].median())
        for name, p in [("hedonic", pred), ("segment median", base)]:
            err = np.exp(p) - test["price"]
            rows.append({
                "fold": k, "model": name,
                "rmse_log": float(np.sqrt(np.mean((p - test["log_price"]) ** 2))),
                "mape": float(np.mean(np.abs(err) / test["price"])),
                "r2_log": float(1 - np.sum((test["log_price"] - p) ** 2)
                                / np.sum((test["log_price"] - test["log_price"].mean()) ** 2)),
            })
    return pd.DataFrame(rows)


def effects(fit, prefix: str, label: str) -> pd.DataFrame:
    ci = fit.conf_int()
    keep = [k for k in fit.params.index if k.startswith(prefix)]
    return pd.DataFrame({
        label: [k.split("[T.")[1].rstrip("]") for k in keep],
        "pct": (np.exp(fit.params[keep]) - 1) * 100,
        "ci_lo": (np.exp(ci.loc[keep, 0]) - 1) * 100,
        "ci_hi": (np.exp(ci.loc[keep, 1]) - 1) * 100,
        "p_value": fit.pvalues[keep],
    }).reset_index(drop=True)


def state_premiums(df: pd.DataFrame, fit) -> pd.DataFrame:
    """Raw median gap vs mix-adjusted premium, both relative to NSW."""
    adj = effects(fit, "C(state", "state")
    nsw = {"state": "NSW", "pct": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "p_value": 1.0}
    adj = pd.concat([adj, pd.DataFrame([nsw])])
    raw = df.groupby("state")["price"].agg(["median", "size"])
    raw = raw.rename(columns={"median": "raw_median", "size": "n"})
    raw["raw_pct"] = (raw["raw_median"] / raw.loc["NSW", "raw_median"] - 1) * 100
    out = adj.merge(raw.reset_index(), on="state").rename(columns={"pct": "adjusted_pct"})
    return out.sort_values("adjusted_pct", ascending=False).reset_index(drop=True)


def depreciation_curves(df: pd.DataFrame, max_age: int = 15) -> pd.DataFrame:
    """Share of new price retained by age, per segment, from a segment x age interaction model."""
    d = model_frame(df)
    d = d[d["body_type"].isin(SEGMENTS)]
    fit = smf.ols(
        "log_price ~ C(body_type) * (age + I(age**2)) + log_km + C(brand_g) + C(state) + C(fuel_type)",
        data=d,
    ).fit(cov_type="HC3")
    rows = []
    for seg in SEGMENTS:
        for age in range(max_age + 1):
            # Contrast against age 0 of the same segment, so the interval is zero-width at age 0
            c = pd.Series(0.0, index=fit.params.index)
            c["age"], c["I(age ** 2)"] = age, age**2
            if f"C(body_type)[T.{seg}]:age" in c.index:
                c[f"C(body_type)[T.{seg}]:age"] = age
                c[f"C(body_type)[T.{seg}]:I(age ** 2)"] = age**2
            est, se = float(c @ fit.params), float(np.sqrt(c @ fit.cov_params() @ c))
            rows.append({"segment": seg, "age": age, "retained": np.exp(est),
                         "retained_lo": np.exp(est - Z95 * se), "retained_hi": np.exp(est + Z95 * se)})
    return pd.DataFrame(rows)


def brand_retention(df: pd.DataFrame, at_age: int = 5) -> pd.DataFrame:
    """Value retained at a given age per brand, holding segment, km, state and fuel fixed."""
    d = model_frame(df)
    d = d[(d["brand_g"] != "Other") & (d["age"] <= 15)]
    fit = smf.ols(
        "log_price ~ C(brand_g) * age + I(age**2) + log_km + C(body_type) + C(state) + C(fuel_type)", data=d
    ).fit(cov_type="HC3")
    rows = []
    for b in sorted(d["brand_g"].unique()):
        # Log price change from age 0 to at_age for this brand, everything else held fixed
        diff = pd.Series(0.0, index=fit.params.index)
        diff["age"] = at_age
        diff["I(age ** 2)"] = at_age**2
        interaction = f"C(brand_g)[T.{b}]:age"
        if interaction in diff.index:
            diff[interaction] = at_age
        est = float(diff @ fit.params)
        se = float(np.sqrt(diff @ fit.cov_params() @ diff))
        rows.append({
            "brand": b, "n": int((d["brand_g"] == b).sum()),
            "retained": np.exp(est), "ci_lo": np.exp(est - Z95 * se), "ci_hi": np.exp(est + Z95 * se),
        })
    return pd.DataFrame(rows).sort_values("retained", ascending=False).reset_index(drop=True)


def ai_panel(prices: pd.DataFrame, seg_prices: pd.DataFrame, earnings: pd.DataFrame,
             premiums: pd.DataFrame) -> pd.DataFrame:
    """Affordability Index by year, state, sex, work status and segment for the dashboard.

    AI = annual median earnings / segment price. Segment prices are 2023 medians moved with the
    national motor vehicles index and scaled by each state's like-for-like premium.
    """
    rel = prices.set_index("year")["car_price"] / prices.set_index("year").loc[SNAPSHOT_YEAR, "car_price"]
    prem = premiums.set_index("state")["adjusted_pct"].to_dict() | {"AUS": 0.0}
    e = earnings[earnings["leave"] == "Total"].copy()
    e = e[e["year"].isin(rel.index)]
    out = e.merge(seg_prices[["segment", "median_price"]], how="cross")
    out["price"] = out["median_price"] * out["year"].map(rel) * (1 + out["state"].map(prem) / 100)
    out["annual_income"] = out["median_weekly"] * 52
    out["ai"] = out["annual_income"] / out["price"]
    cols = ["year", "state", "sex", "work_status", "segment", "annual_income", "price", "ai"]
    return out[cols].round({"annual_income": 0, "price": 0, "ai": 4}).sort_values(cols[:5]).reset_index(drop=True)


# --- Mix shift: buyers moving to SUVs and utes ---


def cohort_mix(df: pd.DataFrame, since: int = 2008) -> pd.DataFrame:
    """Segment share of each model-year cohort still listed in 2023."""
    d = df[(df["year"] >= since) & df["body_type"].isin(SEGMENTS)]
    share = d.groupby("year")["body_type"].value_counts(normalize=True).rename("share").reset_index()
    return share.rename(columns={"body_type": "segment"})


def mix_shift(mix: pd.DataFrame, seg_prices: pd.DataFrame) -> pd.DataFrame:
    """Typical new price at 2023 segment prices under each cohort's segment mix."""
    p = seg_prices.set_index("segment")["median_price"]
    m = mix.assign(weighted=mix["share"] * mix["segment"].map(p))
    out = m.groupby("year")["weighted"].sum().rename("mix_price").reset_index()
    out["vs_2014"] = out["mix_price"] / out.loc[out["year"] == BASE_YEAR, "mix_price"].item() - 1
    suv_ute = mix[mix["segment"].isin(["SUV", "Ute"])].groupby("year")["share"].sum()
    return out.merge(suv_ute.rename("suv_ute_share").reset_index(), on="year")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cpi = pd.read_csv(CLEAN / "cpi_annual.csv")
    awe = pd.read_csv(CLEAN / "awe_annual.csv")
    earn = pd.read_csv(CLEAN / "median_weekly_earnings.csv")
    df = load_listings()

    prices = car_price_series(cpi, typical_new_price(df))
    seg = new_segment_prices(df)
    fit = fit_hedonic(df)
    mix = cohort_mix(df)

    tables = {
        "car_price_series": prices,
        "weeks_by_awe": weeks_by_awe(prices, awe),
        "weeks_by_group": weeks_by_group(prices, earn),
        "new_segment_prices": seg,
        "group_segment_matrix": group_segment_matrix(seg, earn),
        "hedonic_cv": cross_validate(df),
        "state_premiums": (premiums := state_premiums(df, fit)),
        "ai_panel": ai_panel(prices, seg, earn, premiums),
        "segment_effects": effects(fit, "C(body_type", "segment"),
        "depreciation_curves": depreciation_curves(df),
        "brand_retention": brand_retention(df),
        "cohort_mix": mix,
        "mix_shift": mix_shift(mix, seg),
    }
    for name, t in tables.items():
        t.to_csv(OUT / f"{name}.csv", index=False)
    (OUT / "hedonic_summary.txt").write_text(fit.summary().as_text())


if __name__ == "__main__":
    main()
