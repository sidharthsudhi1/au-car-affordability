import pandas as pd
import pytest

from carafford import listings
from carafford.paths import CLEAN, INTERIM

STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT", "AUS"}


@pytest.fixture(scope="module")
def cpi():
    return pd.read_csv(CLEAN / "cpi_annual.csv")


@pytest.fixture(scope="module")
def awe():
    return pd.read_csv(CLEAN / "awe_annual.csv")


@pytest.fixture(scope="module")
def earnings():
    return pd.read_csv(CLEAN / "median_weekly_earnings.csv")


@pytest.fixture(scope="module")
def cars():
    path = INTERIM / "listings_clean.csv"
    if not path.exists():
        pytest.skip("listings not built; Kaggle file not downloaded")
    return pd.read_csv(path)


def test_cpi_complete_panel(cpi):
    # ABS publishes the motor vehicles and fuel indexes nationally only; all groups by capital city
    counts = cpi.groupby(["series", "region"]).size()
    assert set(cpi.loc[cpi["series"] == "all_groups", "region"]) == STATES
    assert set(cpi.loc[cpi["series"] != "all_groups", "region"]) == {"AUS"}
    assert counts.nunique() == 1
    assert not cpi.duplicated(["series", "region", "year"]).any()


def test_cpi_reference_period(cpi):
    aus = cpi[(cpi["region"] == "AUS") & (cpi["series"] == "all_groups")]
    assert aus["index"].between(60, 130).all()
    assert aus["index"].is_monotonic_increasing


def test_awe_regions_and_sexes(awe):
    assert set(awe["region"]) == STATES
    assert set(awe["sex"]) == {"Males", "Females", "Persons"}
    assert awe["weekly_ote"].between(800, 4000).all()


def test_awe_males_above_females(awe):
    wide = awe.pivot_table(index=["region", "year"], columns="sex", values="weekly_ote")
    assert (wide["Males"] > wide["Females"]).all()


def test_earnings_matches_published_headline(earnings):
    # ABS Employee Earnings Aug 2024: national median weekly earnings $1,396 (all employees)
    row = earnings.query(
        "year == 2024 and state == 'AUS' and sex == 'Persons' and work_status == 'Total' and leave == 'Total'"
    )
    assert row["median_weekly"].item() == pytest.approx(1396)


def test_earnings_unique_and_rse_bounded(earnings):
    keys = ["year", "state", "sex", "work_status", "leave"]
    assert not earnings.duplicated(keys).any()
    assert (earnings["rse_pct"].dropna() >= 0).all()
    unreliable = earnings[earnings["reliability"] == "unreliable"]
    assert (unreliable["rse_pct"] > 50).all()
    assert len(unreliable) / len(earnings) < 0.01
    assert set(earnings["state"]) == STATES


def test_full_time_earns_more_than_part_time(earnings):
    tot = earnings[earnings["leave"] == "Total"]
    wide = tot.pivot_table(index=["year", "state", "sex"], columns="work_status", values="median_weekly")
    assert (wide["Full-time"] > wide["Part-time"]).all()


def test_listing_ranges(cars):
    assert cars["price"].between(listings.MIN_PRICE, listings.MAX_PRICE).all()
    assert cars["age"].between(0, listings.MAX_AGE).all()
    assert (cars["km"].dropna() <= listings.MAX_KM).all()
    assert cars["state"].dropna().isin(STATES - {"AUS"}).all()


def test_listing_no_duplicates(cars):
    assert not cars.duplicated(["title", "price", "km", "state"]).any()


def test_listing_split_brands_repaired(cars):
    assert not cars["brand"].isin(["Land", "Alfa", "Aston", "Great"]).any()
    assert {"Land Rover", "Alfa Romeo"} <= set(cars["brand"])


def test_listing_null_rates(cars):
    for col in ["brand", "price", "age", "body_type", "condition"]:
        assert cars[col].notna().all(), col
    assert cars["km"].isna().mean() < 0.05
    assert cars["state"].isna().mean() < 0.05


def test_new_cars_have_low_km(cars):
    new = cars[cars["condition"] == "New"]
    assert (new["km"].dropna() <= listings.MAX_NEW_KM).all()


def test_funnel_accounts_for_every_row():
    log = pd.read_csv(CLEAN / "listings_cleaning_log.csv")
    assert log["rows"].iloc[0] - log["dropped"].sum() == log["rows"].iloc[-1]
