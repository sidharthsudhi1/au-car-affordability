# ============================================================
# Radar Chart: Car Affordability by Segment (2014 vs Latest)
# ============================================================

# Packages
library(tidyverse)
library(readr)
library(janitor)
library(fmsb)
library(scales)

# -----------------------------
# 0) Parameters
# -----------------------------
group_profiles <- c("Persons", "Males", "Females")   # which gender profiles
region_keep    <- "Australia"                        # keep national averages
price_trim     <- c(0.01, 0.99)                      # clamp tails of car prices
segment_order  <- c("Hatchback","Sedan","SUV","Ute/Pickup","Wagon",
                    "People Mover","Commercial","Convertible","Coupe","Other")

# -----------------------------
# 1) Load & clean data
# -----------------------------
abs <- read_csv("abs_income_long_allgroups.csv", show_col_types = FALSE) |>
  clean_names()

veh <- read_csv("vehicle_prices_clean.csv", show_col_types = FALSE) |>
  clean_names()

# -----------------------------
# 2) Earnings (Total × Total)
# -----------------------------
abs_tt <- abs |>
  filter(region == region_keep,
         employment_type == "Total",
         paid_leave == "Total",
         sex %in% group_profiles) |>
  transmute(year,
            sex,
            annual_income_aud = annual_median_aud) |>
  drop_na(year, sex, annual_income_aud)

# -----------------------------
# 3) Car prices (median per segment × year)
# -----------------------------
veh <- veh |>
  filter(!is.na(price), !is.na(bodytype_std)) |>
  mutate(price_clip = {
    q <- quantile(price, probs = price_trim, na.rm = TRUE)
    pmin(pmax(price, q[1]), q[2])
  })

veh_seg_year <- veh %>%
  group_by(year, segment = bodytype_std) %>%   # rename here
  summarise(
    median_car_aud = median(price_clip, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  drop_na(year, segment, median_car_aud)

# -----------------------------
# 4) Build affordability table
# -----------------------------
afford_by_group <- abs_tt %>%
  left_join(veh_seg_year, by = "year") %>%
  mutate(
    affordability_score = annual_income_aud / median_car_aud,
    group_label = paste(sex, "Total", "Total", sep = " - ")
  ) %>%
  select(year, group_label, segment, affordability_score) %>%
  filter(!is.na(year), !is.na(segment), !is.na(affordability_score))

# Enforce consistent segment order
seg_levels <- segment_order[segment_order %in% unique(afford_by_group$segment)]
if (length(seg_levels)) {
  afford_by_group <- afford_by_group %>%
    mutate(segment = factor(segment, levels = seg_levels))
}

# Pick comparison years
years_available <- sort(unique(afford_by_group$year))
y1 <- if (2014 %in% years_available) 2014 else min(years_available)
y2 <- max(years_available)

# -----------------------------
# 5) Radar chart helpers
# -----------------------------
make_radar_frame <- function(df, profile, y1, y2) {
  wide <- df %>%
    filter(group_label == profile, year %in% c(y1, y2)) %>%
    select(year, segment, affordability_score) %>%
    pivot_wider(names_from = segment, values_from = affordability_score)
  
  if (!all(c(y1, y2) %in% wide$year)) return(NULL)
  
  wide <- wide %>%
    arrange(factor(year, levels = c(y1, y2))) %>%
    select(-year)
  
  vmax <- max(as.matrix(wide), na.rm = TRUE)
  vmax <- ceiling(vmax * 1.15 / 0.1) * 0.1
  
  rbind(
    rep(vmax, ncol(wide)),
    rep(0,    ncol(wide)),
    wide
  ) %>% as.data.frame()
}

plot_afford_radar_pretty <- function(profile, y1, y2,
                                     col_y1 = alpha("#2C7BB6", 0.35),
                                     brd_y1 = "#2C7BB6",
                                     col_y2 = alpha("#D7191C", 0.35),
                                     brd_y2 = "#D7191C") {
  rf <- make_radar_frame(afford_by_group, profile, y1, y2)
  if (is.null(rf)) {
    message("Skipping ", profile, " (missing years).")
    return(invisible(NULL))
  }
  
  op <- par(mar = c(1.5, 2, 3.5, 2)); on.exit(par(op), add = TRUE)
  fmsb::radarchart(
    rf,
    axistype = 1,
    seg = 5,
    pcol  = c(brd_y1, brd_y2),
    pfcol = c(col_y1, col_y2),
    plwd  = 2.2,
    plty  = c(1, 2),
    cglcol = "grey80",
    cglty  = 1,
    cglwd  = 0.8,
    axislabcol = "grey35",
    vlcex = 0.9
  )
  legend("topright",
         legend = c(as.character(y1), as.character(y2)),
         bty = "n", cex = 0.9, pch = 15, pt.cex = 1.2,
         col = c(brd_y1, brd_y2), text.col = "grey10")
  title(main = sprintf("Affordability Index by car segment"),
        cex.main = 1.0, col.main = "grey10", font.main = 2)
  mtext("Affordability Score = median annual income ÷ median car price (higher = better). Source : ABS Earnings Data and Redbook Scrape Data",
        side = 1, line = -1, adj = 0, col = "grey35", cex = 0.78)
}

# -----------------------------
# 6) Render all profiles
# -----------------------------
profiles <- paste(group_profiles, "Total", "Total", sep = " - ")

for (p in profiles) {
  plot.new()
  plot_afford_radar_pretty(p, y1 = y1, y2 = y2)
}

plot_afford_radar_pretty(p)
