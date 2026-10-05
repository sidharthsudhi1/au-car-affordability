# AU Car Affordability

How affordable are cars for Australian workers, how has that changed since 2014, and
where in the market does the burden fall?

## Data

| Source | What it gives | Coverage | Licence |
|--------|---------------|----------|---------|
| [ABS Data API](https://data.api.abs.gov.au), CPI | Motor vehicles, fuel and all-groups price indexes | Quarterly 2012-2026, national (all groups by capital city) | CC BY 4.0 |
| [ABS Data API](https://data.api.abs.gov.au), Average Weekly Earnings | Full-time adult ordinary time earnings by sex and state | Half-yearly 2012-2026 | CC BY 4.0 |
| [ABS Employee Earnings, Aug 2024](https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/employee-earnings/aug-2024) | Median weekly earnings by sex, full/part-time, leave entitlement, state, with RSE | Annual (August) 2014-2024 | CC BY 4.0 |
| [Kaggle: Australian Vehicle Prices](https://www.kaggle.com/datasets/nelgiriyewithana/australian-vehicle-prices) | 16.7k car listings: price, age, km, body type, brand, state, new/used | Single 2023 snapshot | Not stated; raw file not redistributed |

The listings are a cross-section, not a time series: `Year` is the model year of a car
listed in 2023, and 90% of listings are used. Price change over time therefore comes
from the ABS motor vehicles index, and the listings are used for market structure
(segments, depreciation, states).

## Wrangling

`make data` rebuilds every table in `data/clean/` from `data/raw/`.

- **ABS API:** SDMX queries for CPI and AWE, tidied and annualised (only years with
  every quarter or half present).
- **Employee Earnings cube:** two-row merged headers (state over value/RSE) melted to
  long format; zero-padded unpublished years nulled; each cell flagged ok / caution /
  unreliable using ABS RSE thresholds.
- **Listings:** brands split across columns ("Land" + "Rover") rebuilt from titles;
  seat counts shifted into the doors column moved back; engine, fuel use, km, doors and
  seats parsed from text; `-` and `POA` placeholders nulled; state parsed from suburb.

Every listing filter is logged ([cleaning log](data/clean/listings_cleaning_log.csv)):

| Step | Rows | Dropped |
|------|-----:|--------:|
| Raw listings | 16,734 | |
| Blank rows | 16,733 | 1 |
| Missing or POA price | 16,681 | 52 |
| Near-duplicate listings | 16,618 | 63 |
| Price outside $2k-$400k | 16,593 | 25 |
| Older than 20 years | 16,333 | 260 |
| Over 500,000 km | 16,328 | 5 |
| "New" with over 5,000 km | 16,327 | 1 |
| Unknown body type | 16,043 | 284 |

`make test` runs 18 checks: parser unit tests plus data validation (complete panels,
published ABS headline reproduced, ranges, duplicates, null rates, funnel arithmetic).

## Reproduce

```
make setup
make fetch   # pulls ABS series; place the Kaggle CSV at data/raw/australian_vehicle_prices.csv first
make test
```
