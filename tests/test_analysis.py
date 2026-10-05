import numpy as np
import pandas as pd
import pytest

from carafford import analysis
from carafford.paths import CLEAN

OUT = CLEAN / "analysis"


def cpi_frame():
    rows = []
    for year, mv, ag in [(2014, 80.0, 70.0), (2023, 100.0, 90.0)]:
        rows += [{"series": "motor_vehicles", "region": "AUS", "year": year, "index": mv},
                 {"series": "all_groups", "region": "AUS", "year": year, "index": ag}]
    return pd.DataFrame(rows)


def test_car_price_series_anchors_snapshot_year():
    s = analysis.car_price_series(cpi_frame(), 50_000).set_index("year")
    assert s.loc[2023, "car_price"] == 50_000
    assert s.loc[2014, "car_price"] == pytest.approx(40_000)
    assert s.loc[2014, "real_car_index"] == 1.0


def test_group_weeks_interval_brackets_estimate():
    prices = pd.DataFrame({"year": [2023], "car_price": [52_000.0]})
    earn = pd.DataFrame([{"year": 2023, "state": "AUS", "leave": "Total", "sex": "Persons",
                          "work_status": "Full-time", "median_weekly": 1600.0, "rse_pct": 2.0}])
    g = analysis.weeks_by_group(prices, earn).iloc[0]
    assert g["weeks"] == pytest.approx(32.5)
    assert g["weeks_lo"] < g["weeks"] < g["weeks_hi"]


def test_bootstrap_median_interval_contains_median():
    x = np.random.default_rng(0).lognormal(10, 0.5, 500)
    med, lo, hi = analysis.bootstrap_median(x)
    assert lo < med < hi


def test_mix_shift_zero_at_base_year():
    mix = pd.DataFrame({"year": [2014, 2014, 2023, 2023], "segment": ["SUV", "Hatchback"] * 2,
                        "share": [0.5, 0.5, 0.8, 0.2]})
    prices = pd.DataFrame({"segment": ["SUV", "Hatchback"], "median_price": [50_000.0, 30_000.0]})
    out = analysis.mix_shift(mix, prices).set_index("year")
    assert out.loc[2014, "vs_2014"] == 0
    assert out.loc[2023, "mix_price"] == pytest.approx(46_000)


@pytest.fixture(scope="module")
def tables():
    if not (OUT / "state_premiums.csv").exists():
        pytest.skip("analysis tables not built")
    return {p.stem: pd.read_csv(p) for p in OUT.glob("*.csv")}


def test_hedonic_beats_baseline_out_of_sample(tables):
    cv = tables["hedonic_cv"].groupby("model")["mape"].mean()
    assert cv["hedonic"] < cv["segment median"]


def test_retention_curves_start_at_one_and_decline(tables):
    for _, g in tables["depreciation_curves"].groupby("segment"):
        g = g.sort_values("age")
        assert g["retained"].iloc[0] == pytest.approx(1.0)
        assert g["retained"].is_monotonic_decreasing


def test_brand_retention_is_a_share(tables):
    b = tables["brand_retention"]
    assert b["retained"].between(0, 1).all()
    assert (b["ci_lo"] <= b["retained"]).all() and (b["retained"] <= b["ci_hi"]).all()


def test_state_premium_baseline(tables):
    s = tables["state_premiums"].set_index("state")
    assert s.loc["NSW", "adjusted_pct"] == 0
    assert len(s) == 8


def test_cohort_mix_sums_to_one(tables):
    assert np.allclose(tables["cohort_mix"].groupby("year")["share"].sum(), 1)


def test_ai_panel_is_income_over_price(tables):
    p = tables["ai_panel"]
    assert np.allclose(p["ai"], p["annual_income"] / p["price"], rtol=1e-3)
    assert p.groupby(["year", "state", "sex", "work_status"]).size().eq(5).all()
    nsw = p[(p["state"] == "NSW") & (p["year"] == 2023)].groupby("segment")["price"].first()
    aus = p[(p["state"] == "AUS") & (p["year"] == 2023)].groupby("segment")["price"].first()
    assert np.allclose(nsw, aus, atol=1)
