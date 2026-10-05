"""Static figures for the README and notebook. Run: python -m carafford.figures"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from matplotlib.colors import ListedColormap
from matplotlib.ticker import FuncFormatter, PercentFormatter

from carafford import analysis
from carafford.analysis import OUT as TABLES
from carafford.analysis import SEGMENTS
from carafford.paths import FIGURES

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e6e5e1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEGMENT_COLOR = dict(zip(SEGMENTS, SERIES, strict=True))

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.size": 10.5, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.titlepad": 22, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "xtick.color": INK_2, "ytick.color": INK_2, "xtick.major.size": 0, "ytick.major.size": 0,
    "lines.linewidth": 2, "legend.frameon": False, "figure.dpi": 110, "savefig.dpi": 200,
})

dollars = FuncFormatter(lambda v, _: f"${v / 1000:.0f}k")


def table(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES / f"{name}.csv")


def subtitle(ax, text: str) -> None:
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=10, va="bottom")


def source(fig, text: str) -> None:
    fig.text(0.01, -0.02, text, color=MUTED, fontsize=8, ha="left", va="top")


def dodge(values, gap: float) -> np.ndarray:
    """Spread label positions so neighbours sit at least `gap` apart, preserving order."""
    order = np.argsort(values)
    pos = np.asarray(values, dtype=float)[order].copy()
    for i in range(1, len(pos)):
        pos[i] = max(pos[i], pos[i - 1] + gap)
    out = np.empty_like(pos)
    out[order] = pos - (pos.mean() - np.mean(values))
    return out


def save(fig, name: str) -> None:
    FIGURES.mkdir(exist_ok=True)
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight", pad_inches=0.25)


def weeks_to_buy():
    w = table("weeks_by_awe").query("region == 'AUS' and sex == 'Persons'")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(w["year"], w["weeks"], color=SERIES[0], marker="o", markersize=5,
            markeredgecolor=SURFACE, markeredgewidth=2)
    for _, r in w[w["year"].isin([2014, 2020, 2023, w["year"].max()])].iterrows():
        ax.annotate(f"{r['weeks']:.1f}", (r["year"], r["weeks"]), textcoords="offset points",
                    xytext=(0, 9), ha="center", color=INK, fontsize=10, fontweight="bold")
    ax.axvspan(2020.5, 2023.5, color=GRID, alpha=0.5, lw=0)
    ax.text(2022, 25.3, "supply shortage", ha="center", color=INK_2, fontsize=9)
    ax.set_ylim(24.5, 33)
    ax.set_xticks(w["year"])
    ax.set_ylabel("weeks of earnings")
    ax.set_title("A typical new car costs 5 fewer weeks of pay than in 2014")
    subtitle(ax, "Full-time adult earnings vs the median 2023 new car, back-cast with the ABS motor vehicles index")
    source(fig, "Source: ABS CPI and Average Weekly Earnings; Kaggle Australian Vehicle Prices (2023 anchor)")
    return fig


def indexed_growth():
    p = table("car_price_series").set_index("year")
    awe = table("weeks_by_awe").query("region == 'AUS' and sex == 'Persons'").set_index("year")["weekly_ote"]
    p = p.loc[2014:]
    series = {
        "Earnings": awe / awe.loc[2014] * 100,
        "All prices (CPI)": p["all_groups_index"] / p.loc[2014, "all_groups_index"] * 100,
        "Car prices": p["motor_vehicles_index"] / p.loc[2014, "motor_vehicles_index"] * 100,
    }
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for (name, s), c in zip(series.items(), SERIES[:3], strict=True):
        ax.plot(s.index, s.values, color=c)
        ax.text(s.index[-1] + 0.25, s.values[-1], f"{name}  {s.values[-1]:.0f}", color=INK, va="center",
                fontsize=10)
        ax.plot(s.index[-1], s.values[-1], "o", color=c, markersize=6, markeredgecolor=SURFACE,
                markeredgewidth=2)
    ax.axhline(100, color=INK_2, lw=0.8)
    ax.set_xlim(2013.6, 2028.2)
    ax.set_xticks(range(2014, 2026, 2))
    ax.set_ylabel("index, 2014 = 100")
    ax.set_title("Earnings outran car prices, even through the 2021-23 spike")
    subtitle(ax, "Calendar-year averages. Car prices are quality adjusted, so mix shifts are excluded")
    source(fig, "Source: ABS CPI (motor vehicles, all groups), Average Weekly Earnings (full-time adult OTE)")
    return fig


def group_weeks():
    g = table("weeks_by_group")
    g = g[g["sex"].isin(["Males", "Females"]) & g["work_status"].isin(["Full-time", "Part-time"])]
    g = g[g["year"].isin([2014, 2024])].copy()
    g["group"] = g["work_status"] + " " + g["sex"].str.lower()
    order = g[g["year"] == 2024].sort_values("weeks")["group"].tolist()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for i, grp in enumerate(order):
        a = g[(g["group"] == grp) & (g["year"] == 2014)].iloc[0]
        b = g[(g["group"] == grp) & (g["year"] == 2024)].iloc[0]
        ax.plot([b["weeks"], a["weeks"]], [i, i], color=GRID, lw=3, solid_capstyle="round", zorder=1)
        ax.errorbar(a["weeks"], i, xerr=[[a["weeks"] - a["weeks_lo"]], [a["weeks_hi"] - a["weeks"]]],
                    fmt="o", color=SERIES[1], ms=8, mec=SURFACE, mew=2, elinewidth=1.2, zorder=3)
        ax.errorbar(b["weeks"], i, xerr=[[b["weeks"] - b["weeks_lo"]], [b["weeks_hi"] - b["weeks"]]],
                    fmt="o", color=SERIES[0], ms=8, mec=SURFACE, mew=2, elinewidth=1.2, zorder=3)
        ax.text(a["weeks_hi"] + 2, i, f"{a['weeks']:.0f}", va="center", color=INK_2, fontsize=9)
        ax.text(b["weeks_lo"] - 2, i, f"{b['weeks']:.0f}", va="center", ha="right", color=INK, fontsize=9,
                fontweight="bold")
    ax.set_yticks(range(len(order)), order)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(0, 125)
    ax.set_xlabel("weeks of median earnings to buy the typical new car")
    ax.plot([], [], "o", color=SERIES[1], label="2014")
    ax.plot([], [], "o", color=SERIES[0], label="2024")
    ax.legend(loc="lower right", ncols=2)
    ax.set_title("Part-time workers need 2.5x the weeks; every group improved")
    subtitle(ax, "Median weekly earnings, all jobs. Whiskers are 95% intervals from ABS standard errors")
    source(fig, "Source: ABS Employee Earnings (Aug), CPI; Kaggle listings for the 2023 price anchor")
    return fig


def state_premiums():
    s = table("state_premiums").sort_values("adjusted_pct")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = np.arange(len(s))
    ax.axvline(0, color=INK_2, lw=0.8)
    ax.scatter(s["raw_pct"], y, s=60, facecolors=SURFACE, edgecolors=MUTED, linewidths=1.5, zorder=2,
               label="raw median gap")
    err = [s["adjusted_pct"] - s["ci_lo"], s["ci_hi"] - s["adjusted_pct"]]
    ax.errorbar(s["adjusted_pct"], y, xerr=err,
                fmt="o", color=SERIES[0], ms=8, mec=SURFACE, mew=2, elinewidth=1.2, zorder=3,
                label="like-for-like premium (95% CI)")
    for yi, (_, r) in zip(y, s.iterrows(), strict=True):
        sig = r["p_value"] < 0.05 and r["state"] != "NSW"
        label = f"{r['adjusted_pct']:+.1f}%" + (" *" if sig else "")
        ax.text(max(r["raw_pct"], r["ci_hi"]) + 1.2, yi, label, va="center", color=INK if sig else INK_2,
                fontsize=9, fontweight="bold" if sig else "normal")
    ax.set_yticks(y, [f"{st}  (n={n:,})" for st, n in zip(s["state"], s["n"], strict=True)])
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(PercentFormatter(decimals=0))
    ax.set_xlim(-10, 28)
    ax.set_xlabel("price vs NSW")
    ax.legend(loc="center right")
    ax.set_title("Tasmania's 21% price gap is the cars, not the state")
    subtitle(ax, "Hedonic model holds age, km, segment, brand, fuel, gearbox and drive fixed. * p < 0.05")
    source(fig, "Source: Kaggle Australian Vehicle Prices (2023), 15,109 listings with complete attributes")
    return fig


def depreciation():
    d = table("depreciation_curves")
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for seg in SEGMENTS:
        g = d[d["segment"] == seg]
        c = SEGMENT_COLOR[seg]
        ax.fill_between(g["age"], g["retained_lo"], g["retained_hi"], color=c, alpha=0.15, lw=0)
        ax.plot(g["age"], g["retained"], color=c)
        ax.plot(g["age"].iloc[-1], g["retained"].iloc[-1], "o", color=c, ms=6, mec=SURFACE, mew=2)
    five = d[d["age"] == 5].set_index("segment")["retained"]
    end = d[d["age"] == d["age"].max()].set_index("segment")["retained"]
    for seg, yp in zip(end.index, dodge(end.values, 0.045), strict=True):
        ax.text(d["age"].max() + 0.4, yp, f"{seg}  {five[seg]:.0%} at 5 yrs", va="center", color=INK,
                fontsize=10)
    ax.set_xlim(0, d["age"].max() + 5.5)
    ax.set_xticks(range(0, 16, 5))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 1.04)
    ax.set_xlabel("age (years)")
    ax.set_ylabel("share of new price retained")
    ax.set_title("Hatchbacks hold value best; wagons and sedans lose half in five years")
    subtitle(ax, "Modelled value retained by segment, same brand, km, state and fuel. Bands are 95% CIs")
    source(fig, "Source: Kaggle Australian Vehicle Prices (2023), segment x age interaction model")
    return fig


def brand_retention():
    b = table("brand_retention").sort_values("retained")
    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(b))
    colors = [SERIES[0] if r >= b["retained"].median() else MUTED for r in b["retained"]]
    ax.hlines(y, b["ci_lo"], b["ci_hi"], color=colors, lw=1.4)
    ax.scatter(b["retained"], y, color=colors, s=60, edgecolors=SURFACE, linewidths=2, zorder=3)
    for yi, (_, r) in zip(y, b.iterrows(), strict=True):
        ax.text(r["ci_hi"] + 0.006, yi, f"{r['retained']:.0%}", va="center", color=INK_2, fontsize=9)
    ax.set_yticks(y, b["brand"])
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("value retained after 5 years")
    ax.set_title("Toyota keeps 72% of its value at five years; BMW and Mercedes 53%")
    subtitle(ax, "Brand x age model, segment, km, state and fuel fixed. Lines are 95% CIs; blue = above median")
    source(fig, "Source: Kaggle Australian Vehicle Prices (2023), 15 most-listed brands, cars up to 15 years")
    return fig


def cohort_mix():
    m = table("cohort_mix").pivot(index="year", columns="segment", values="share").fillna(0)[SEGMENTS]
    stack = ["SUV", "Ute", "Wagon", "Sedan", "Hatchback"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.stackplot(m.index, [m[s] for s in stack], colors=[SEGMENT_COLOR[s] for s in stack],
                 edgecolor=SURFACE, linewidth=1.5, alpha=0.9)
    cum = m[stack].cumsum(axis=1)
    last = m.index.max()
    for s in stack:
        mid = cum.loc[last, s] - m.loc[last, s] / 2
        ax.text(last + 0.3, mid, f"{s}  {m.loc[last, s]:.0%}", va="center", color=INK, fontsize=10)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_xlim(m.index.min(), last + 3.2)
    ax.set_xticks(range(m.index.min(), last + 1, 3))
    ax.set_ylim(0, 1)
    ax.grid(False)
    ax.set_xlabel("model year")
    ax.set_ylabel("share of listings")
    ax.set_title("SUVs and utes: half of 2014 models, four in five 2023 models")
    subtitle(ax, "Segment mix of each model-year cohort listed for sale in 2023")
    source(fig, "Source: Kaggle Australian Vehicle Prices (2023). Older cohorts reflect survival, not just sales")
    return fig


def group_segment_heatmap():
    m = table("group_segment_matrix")
    order_g = m.groupby("group")["weeks"].mean().sort_values().index
    order_s = m.groupby("segment")["median_price"].first().sort_values().index
    grid = m.pivot(index="group", columns="segment", values="weeks").loc[order_g, order_s]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bins = np.array([0, 25, 40, 55, 70, 85, 100, 200])
    idx = np.digitize(grid.values, bins) - 1
    ax.imshow(idx, cmap=ListedColormap(SEQ), aspect="auto", vmin=0, vmax=len(SEQ) - 1)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v = grid.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=10,
                    color="white" if idx[i, j] >= 3 else INK)
    prices = m.groupby("segment")["median_price"].first()
    ax.set_xticks(range(len(order_s)), [f"{s}\n${prices[s] / 1000:.0f}k" for s in order_s])
    ax.set_yticks(range(len(order_g)), order_g)
    ax.grid(False)
    ax.tick_params(axis="x", labeltop=True, labelbottom=False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Weeks of median pay to buy a new car, 2023", pad=48)
    source(fig, "Source: ABS Employee Earnings Aug 2023; median new/demo listing price by segment (Kaggle)")
    return fig


def model_fit():
    df = analysis.model_frame(analysis.load_listings())
    fold_of = np.random.default_rng(analysis.SEED).permutation(len(df)) % 5
    train, test = df[fold_of != 0], df[fold_of == 0]
    pred = np.exp(smf.ols(analysis.HEDONIC, data=train).fit().predict(test))
    cv = table("hedonic_cv").groupby("model")[["r2_log", "mape"]].mean()
    fig, ax = plt.subplots(figsize=(6, 5.4))
    hb = ax.hexbin(test["price"], pred, gridsize=45, xscale="log", yscale="log", mincnt=1,
                   cmap=ListedColormap(SEQ[1:]), bins="log", lw=0)
    lim = [3_000, 300_000]
    ax.plot(lim, lim, color=INK_2, lw=1)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.xaxis.set_major_formatter(dollars)
    ax.yaxis.set_major_formatter(dollars)
    ax.set_xlabel("listed price")
    ax.set_ylabel("predicted price (held out)")
    ax.set_title("Hedonic model on held-out listings")
    h, s = cv.loc["hedonic"], cv.loc["segment median"]
    subtitle(ax, f"5-fold CV: R² {h['r2_log']:.2f} on log price, MAPE {h['mape']:.0%} "
                 f"(segment median baseline {s['mape']:.0%})")
    fig.colorbar(hb, ax=ax, label="listings per cell", shrink=0.8, format=FuncFormatter(lambda v, _: f"{v:.0f}"))
    source(fig, "Source: Kaggle Australian Vehicle Prices (2023)")
    return fig


ALL = {
    "01_weeks_to_buy": weeks_to_buy,
    "02_indexed_growth": indexed_growth,
    "03_group_weeks": group_weeks,
    "04_group_segment": group_segment_heatmap,
    "05_state_premiums": state_premiums,
    "06_depreciation": depreciation,
    "07_brand_retention": brand_retention,
    "08_cohort_mix": cohort_mix,
    "09_model_fit": model_fit,
}


def main() -> None:
    for name, make in ALL.items():
        save(make(), name)
        plt.close("all")


if __name__ == "__main__":
    main()
