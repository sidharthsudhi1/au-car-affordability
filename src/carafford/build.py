"""Build every clean table from data/raw. Run: python -m carafford.build [--fetch]"""

import sys

import pandas as pd

from carafford import abs_api, earnings, listings
from carafford.paths import AWE_RAW, CLEAN, CPI_RAW, EARNINGS_RAW, INTERIM, LISTINGS_RAW


def build_abs() -> None:
    cpi = abs_api.tidy_cpi(pd.read_csv(CPI_RAW))
    cpi.to_csv(CLEAN / "cpi_quarterly.csv", index=False)
    abs_api.annual(cpi, "index", ["series", "region"], 4).to_csv(CLEAN / "cpi_annual.csv", index=False)

    awe = abs_api.tidy_awe(pd.read_csv(AWE_RAW))
    awe.to_csv(CLEAN / "awe_halfyearly.csv", index=False)
    abs_api.annual(awe, "weekly_ote", ["region", "sex"], 2).to_csv(CLEAN / "awe_annual.csv", index=False)

    cube = earnings.read_cube(EARNINGS_RAW)
    earnings.median_weekly(cube).to_csv(CLEAN / "median_weekly_earnings.csv", index=False)


def build_listings() -> None:
    if not LISTINGS_RAW.exists():
        sys.exit(f"Missing {LISTINGS_RAW.name}. Download it from Kaggle (see README).")
    clean, funnel = listings.clean(pd.read_csv(LISTINGS_RAW, dtype=str))
    INTERIM.mkdir(parents=True, exist_ok=True)
    clean.to_csv(INTERIM / "listings_clean.csv", index=False)
    funnel.to_csv(CLEAN / "listings_cleaning_log.csv", index=False)


def main() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    if "--fetch" in sys.argv:
        abs_api.download()
    build_abs()
    build_listings()


if __name__ == "__main__":
    main()
