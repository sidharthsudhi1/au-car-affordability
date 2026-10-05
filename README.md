# Assessing the Affordability of Cars in Australia

[![ci](https://github.com/sidharthsudhi1/au-car-affordability/actions/workflows/ci.yml/badge.svg)](https://github.com/sidharthsudhi1/au-car-affordability/actions/workflows/ci.yml)

How many new cars does a year's median pay buy in Australia, how has that changed since 2014,
and which segments, states and worker groups are left behind?

A data exploration and visualisation project from Monash FIT5147: data collection and
wrangling in Python and R, visual exploration in R and Tableau, a Five Design Sheet design
process, and an interactive narrative visualisation in D3.

**[Interactive dashboard](https://sidharthsudhi1.github.io/au-car-affordability/dashboard/)** ·
**[Analysis notebook](notebooks/analysis.ipynb)** ·
**[Design sheets](design/)**

![Affordability heatmap by worker group](figures/r/02_ai_heatmap.png)

## Skills

| Area | What this repo shows | Where |
|------|----------------------|-------|
| Web scraping | Selenium navigation and BeautifulSoup parsing of Redbook detail pages, with robots.txt check and polite delays | [`scraping/`](scraping/redbook_scraper.py) |
| API data collection | SDMX queries against the ABS Data API for CPI and earnings | [`abs_api.py`](src/carafford/abs_api.py) |
| Data wrangling (Python) | Multi-level ABS headers melted to tidy form, broken columns repaired, text fields parsed, every filter logged | [`earnings.py`](src/carafford/earnings.py), [`listings.py`](src/carafford/listings.py) |
| Data wrangling (R) | dplyr/tidyr joins and reshapes to build the Affordability Index | [`r/common.R`](r/common.R) |
| Exploratory visualisation (R) | ggplot2 lollipop, `geom_tile` heatmap, `fmsb` radar, `ggdist` raincloud, grouped bars | [`r/`](r/), [`figures/r/`](figures/r/) |
| Visual design | Five Design Sheets, Munzner's What-Why-How, colourblind-validated palette | [`design/`](design/), below |
| Interactive visualisation (D3) | Linked timeline, choropleth with drill-down bars, Sankey, global filters, tooltips, light/dark, phone layout | [`dashboard/`](dashboard/index.html) |
| Statistical analysis | Hedonic regression with robust errors, cross-validation, bootstrap and RSE-based intervals | [`analysis.py`](src/carafford/analysis.py) |
| Reproducibility | `make` pipeline, 30 pytest checks, CI on every PR | [`Makefile`](Makefile), [`tests/`](tests/) |

## Design process

The dashboard was planned with the Five Design Sheet method: brainstorm and filter idioms,
three alternative layouts, then a final realisation sheet specifying layout, operations
(year slider, segment filter, state click, flow hover) and focus views.

| Sheet 1: brainstorm | Sheets 2-4: alternatives | Sheet 5: realisation |
|---|---|---|
| [![](design/sheet-1.jpg)](design/sheet-1.jpg) | [![](design/sheet-2.jpg)](design/sheet-2.jpg) [![](design/sheet-3.jpg)](design/sheet-3.jpg) [![](design/sheet-4.jpg)](design/sheet-4.jpg) | [![](design/sheet-5.jpg)](design/sheet-5.jpg) |

**What:** a 2014-2024 time series, categorical segments and worker groups (sex x full/part-time),
and state geography, joined through a derived Affordability Index (AI = annual median earnings /
median new price). **Why:** identify national trends, compare segments and groups, and locate
regional differences. **How:** a multi-line timeline (position on a common scale for slopes),
a choropleth paired with a ranked bar panel (overview plus accurate magnitude), and a Sankey
from groups to segments (link width for magnitude), all driven by one control bar.

## Interactive dashboard

[![Dashboard](figures/dashboard.png)](https://sidharthsudhi1.github.io/au-car-affordability/dashboard/)

The [live page](https://sidharthsudhi1.github.io/au-car-affordability/dashboard/) implements sheet 5:
a global year slider, segment and earner filters; a segment-wise AI timeline; a state choropleth
whose click drives a segment bar panel with national comparison ticks; and a Sankey from
employment groups to segments that switches between AI and weeks of pay. Every chart has hover
details and a table view.

## Exploration in R

| | |
|---|---|
| ![](figures/r/01_income_lollipop.png) | ![](figures/r/03_segment_radar.png) |
| ![](figures/r/04_price_raincloud.png) | ![](figures/r/05_brand_grouped_bar.png) |

## Findings

- **Cars became more affordable.** The AI for all employees rose about 20% from 2014 to 2024: earnings grew 40% while quality-adjusted car prices grew about 16%. The 2021-23 supply shortage paused the gain without reversing it.
- **Work status dominates.** In 2024 a full-time worker's pay buys about 2.5 times as much car as a part-time worker's. Part-time men need the most weeks of pay (52 for a hatchback, 112 for a sedan).
- **Hatchbacks are the affordable segment, and they are disappearing.** Cheapest new ($32k median) and slowest to depreciate, but only 8% of 2023 models, while SUVs and utes rose from 51% of 2014 models to 79%.
- **State differences are mostly mix.** Tasmania's 21% raw price gap disappears like-for-like; Victoria (+4.6%) and WA (+2.6%) carry real premiums. ACT has the highest AI because its earnings are highest.
- **Brand drives resale.** Toyota keeps 72% of its value after five years; BMW and Mercedes-Benz 53%.

## Data and wrangling

| Source | Used for | Licence |
|--------|----------|---------|
| [ABS Data API](https://data.api.abs.gov.au): CPI | Motor vehicles and all-groups price indexes, quarterly | CC BY 4.0 |
| [ABS Data API](https://data.api.abs.gov.au): Average Weekly Earnings | Full-time adult earnings by sex and state | CC BY 4.0 |
| [ABS Employee Earnings](https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/employee-earnings/aug-2024) | Median weekly earnings by sex, full/part-time and state with standard errors, 2014-2024 | CC BY 4.0 |
| [Kaggle: Australian Vehicle Prices](https://www.kaggle.com/datasets/nelgiriyewithana/australian-vehicle-prices) | 16.7k listings: price, age, km, segment, brand, state | Not stated; raw file not redistributed |
| [Natural Earth](https://www.naturalearthdata.com) | State boundaries | Public domain |

**A data audit changed the method.** The listings are a single 2023 snapshot and 90% are used
cars, so `Year` is a car's model year rather than when its price was observed. Price by model
year therefore measures depreciation, not price change. Change over time now comes from the ABS
motor vehicles index, anchored in dollars to each segment's 2023 median new listing; the
listings drive segment, brand, state and depreciation comparisons.

Wrangling steps, each logged ([cleaning log](data/clean/listings_cleaning_log.csv)):

- ABS Employee Earnings cube: merged two-row headers (state over value/RSE) melted to long form; zero-padded unpublished years nulled; cells flagged ok / caution / unreliable from ABS standard error thresholds.
- Listings: brands split across columns ("Land" + "Rover") rebuilt from titles; seat counts shifted into the doors column moved back; engine, cylinders, fuel use, km, doors and seats parsed from text; `-` and `POA` nulled; state parsed from suburb strings; 16,734 rows to 16,043 after logged filters.

## Analysis extension

A hedonic regression (log price on age, km, segment, brand, state, fuel, gearbox and drive, HC3
errors) separates like-for-like price differences from mix. 5-fold cross-validation: out-of-sample
R² 0.72, MAPE 25% against 53% for a segment-median baseline. The
[notebook](notebooks/analysis.ipynb) walks through the full analysis.

| | |
|---|---|
| ![](figures/05_state_premiums.png) | ![](figures/06_depreciation.png) |

## Reproduce

```
make setup
make fetch          # ABS series; place the Kaggle CSV at data/raw/australian_vehicle_prices.csv first
make tables figures r notebook
make test
python -m http.server   # then open http://localhost:8000/dashboard/
```

```
scraping/        Selenium + BeautifulSoup scraper
src/carafford/   Python wrangling, analysis and figures
r/               R wrangling and exploratory figures
dashboard/       D3 dashboard and state boundaries
design/          five design sheets
data/clean/      tidy tables and analysis outputs
notebooks/       end-to-end analysis
tests/           pytest suite
```

## Limitations

- The motor vehicles index is national and quality adjusted, so segment and state prices move together over time; their differences come from the 2023 listings.
- Listing prices are asking prices from one snapshot, not transactions.
- Earnings are per employee; household income and the self-employed are out of scope.
- Redbook now blocks automated browsers, so the scraper documents the collection method and the analysis uses the Kaggle listings.
