# AU Car Affordability

How has new-car affordability in Australia changed against income between 2014 and 2023,
and for which segments, regions and worker groups?

An end-to-end data project: scraping and wrangling messy price listings, joining them to
official earnings statistics, building an affordability metric, and communicating the
results through exploratory figures and an interactive D3 dashboard.

## Data wrangling

- **Vehicle prices:** Redbook new car listings collected with Selenium and BeautifulSoup.
  Cleaning handles duplicate listings, inconsistent body type labels, year/brand/model
  embedded in free-text titles, and extreme price outliers.
- **Income:** ABS Average Weekly Earnings by sex, employment type and state, reshaped
  from multi-level headers into tidy long format and annualised.
- **Join:** prices and incomes aligned by year (and state for regional views) into
  analysis-ready tables in `data/clean/`.

## Analysis

Affordability Index (AI) = annual median income / median car price, also rebased to
2014 = 1.0 so changes read as relative shifts.

- Price trends by body type and brand
- Affordability by sex x employment group
- Affordability by state and vehicle segment

## Visualisation

- Exploratory figures in R (ggplot2, fmsb) and Tableau: raincloud plots, grouped bars,
  heatmaps, radar charts (`docs/figures/`)
- Interactive narrative dashboard in D3.js: segment timeline, state choropleth with
  linked ranking, employment group to segment Sankey (`dashboard/`)

## Repo layout

```
scraping/          Redbook scraper
analysis/python/   price cleaning
analysis/r/        income reshaping, affordability, figures
data/clean/        analysis-ready CSVs
dashboard/         D3 dashboard
docs/figures/      exploratory figures
```

## Run the dashboard

The dashboard fetches CSVs, so serve the repo root over HTTP:

```
python -m http.server 5500
```

Open http://localhost:5500/dashboard/index.html
