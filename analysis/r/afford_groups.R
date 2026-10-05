# ============================================================
# RQ2 Data Preparation: Car Affordability by Population Group
# ============================================================
library(dplyr)
library(readr)
library(stringr)

# --- 1) Load datasets ---
# ABS tidy earnings (all groups)
abs_long <- read_csv("abs_income_national_yearly_allgroups.csv", show_col_types = FALSE)

# Vehicle dataset (already cleaned)
veh <- read_csv("vehicle_prices_clean.csv", show_col_types = FALSE)

# --- 2) Median national car price per year (clamp to avoid outliers if not already done) ---
veh_year <- veh %>%
  filter(between(year, 2014, 2024), !is.na(price)) %>%
  group_by(year) %>%
  summarise(median_car_aud = median(price, na.rm = TRUE),
            .groups = "drop")

# --- 3) Merge ABS income with car prices ---
afford <- abs_long %>%
     # keep national aggregates
  left_join(veh_year, by = "year") %>%
  mutate(
    # Key affordability metrics
    affordability_index = median_car_aud / annual_median_aud,     # ratio: car ÷ income
    months_of_income    = affordability_index * 12,               # months of income to buy
  )

# --- 4) Normalise (2014 = 1.0 baseline for index comparisons) ---
afford <- afford %>%
  group_by(sex, employment_type, paid_leave) %>%
  mutate(
    base_2014 = first(affordability_index[year == 2014]),
    affordability_index_2014 = affordability_index / base_2014
  ) %>%
  ungroup()

# --- 5) Create tidy labels for Tableau ---
afford_groups <- afford %>%
  mutate(
    group_family = "Sex × Employment × Leave",
    group_label = paste(sex, employment_type, paid_leave, sep = " - ")
  ) %>%
  select(year, group_family, group_label,
         annual_income_aud = annual_median_aud,
         median_car_aud,
         affordability_index,
         months_of_income,
         base_2014,
         affordability_index_2014)

# --- 6) Save output ---
write_csv(afford_groups, "affordability_by_group_2014_2024.csv")

afford_groups
