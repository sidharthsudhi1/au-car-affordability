# ============================================================
# Affordability Radar — months of income by car segment
# Two overlays: 2014 (baseline) vs 2024 (latest)
# ============================================================
library(tidyverse)
library(scales)
library(readr)
library(janitor)
library(fmsb)        # radar plotting

# -----------------------------
# 0) Parameters you can tweak
# -----------------------------
yrs_compare   <- c(2014, 2024)          # the two years to overlay
use_regions   <- FALSE                  # FALSE = plot by population group; TRUE = plot by region
region_pick   <- c("Australia")         # used if use_regions = TRUE
group_filters <- list(                  # used if use_regions = FALSE (population groups)
  sex              = c("Persons", "Males", "Females"),
  employment_type  = c("Total"),   # keep it tidy; add "Part-time" if you want
  paid_leave       = c("Total")        # use "Total" unless you want With/Without leave
)

# (Optional) outlier clamp for prices so extreme listings don’t skew medians
price_trim_probs <- c(0.01, 0.99)

# -----------------------------
# 1) Load data
# -----------------------------
abs <- read_csv("abs_income_long_allgroups.csv", show_col_types = FALSE) %>%
  clean_names()

veh <- read_csv("vehicle_prices_clean.csv", show_col_types = FALSE) %>%
  clean_names()

# -----------------------------
# 2) Vehicle medians by segment & year
#     (national; clamp price tails to stabilize medians)
# -----------------------------
veh <- veh %>% filter(!is.na(price), between(year, min(yrs_compare), max(yrs_compare)))

trim <- quantile(veh$price, probs = price_trim_probs, na.rm = TRUE)
veh <- veh %>% mutate(price_clip = pmin(pmax(price, trim[1]), trim[2]))

veh_seg_year <- veh %>%
  filter(year %in% yrs_compare, !is.na(bodytype_std)) %>%
  group_by(year, bodytype_std) %>%                 # if you have region in car data, add it here
  summarise(median_car_aud = median(price_clip, na.rm = TRUE), .groups = "drop") %>%
  rename(segment = bodytype_std)

# -----------------------------
# 3) Income: choose population grouping vs regions
# -----------------------------
# -----------------------------
# 3) Income: choose population grouping vs regions (FIXED)
# -----------------------------
abs <- abs %>%
  mutate(
    group_label = paste(sex, employment_type, paid_leave, sep = " - "),
    annual_income_aud = annual_median_aud
  )

if (!use_regions) {
  # 🔧 FIX 1: restrict to national aggregate (Australia) to avoid duplicates
  abs_sel <- abs %>%
    filter(region == "Australia",
           year %in% yrs_compare,
           sex %in% group_filters$sex,
           employment_type %in% group_filters$employment_type,
           paid_leave %in% group_filters$paid_leave) %>%
    # ensure unique per (year, group)
    group_by(year, group_label) %>%
    summarise(annual_income_aud = unique(annual_income_aud)[1], .groups = "drop")
  
  # Cross with segment medians (1 row per year × segment × group)
  afford <- abs_sel %>%
    left_join(veh_seg_year, by = "year") %>%
    mutate(months_of_income = (median_car_aud / annual_income_aud) * 12)
  
  # order groups (optional)
  group_order <- c("Persons - Full-time - Total", "Males - Full-time - Total", "Females - Full-time - Total")
  afford <- afford %>%
    mutate(group_label = factor(group_label, levels = union(group_order, unique(group_label))))
  
} else {
  # Regions mode: fix a single population profile; vary region
  abs_sel <- abs %>%
    filter(year %in% yrs_compare,
           sex == "Persons",
           employment_type == "Full-time",
           paid_leave == "Total",
           region %in% region_pick) %>%
    group_by(year, region) %>%
    summarise(annual_income_aud = unique(annual_income_aud)[1], .groups = "drop")
  
  afford <- abs_sel %>%
    left_join(veh_seg_year, by = "year") %>%
    mutate(months_of_income = (median_car_aud / annual_income_aud) * 12,
           group_label = region)
}

# -----------------------------
# 4) Wide format for radar (robust to any residual dupes)
# -----------------------------
profiles <- unique(afford$group_label)

make_radar_frame <- function(df, profile_name, y1, y2) {
  segs <- df %>%
    filter(group_label == profile_name, year %in% c(y1, y2)) %>%
    select(year, segment, months_of_income) %>%
    # 🔧 FIX 2: if somehow multiple rows remain, average them
    pivot_wider(names_from = segment, values_from = months_of_income,
                values_fn = mean) %>%
    arrange(match(year, c(y1, y2)))
  
  if (!all(c(y1, y2) %in% segs$year)) return(NULL)
  
  segs <- segs %>% select(-year)
  
  # bounds for radar
  max_val <- segs %>% as.matrix() %>% as.numeric() %>% max(na.rm = TRUE)
  max_val <- ceiling(max_val * 1.15 * 2) / 2  # round up to nearest 0.5
  
  radar_df <- rbind(
    rep(max_val, ncol(segs)),   # maxima
    rep(0,       ncol(segs)),   # minima
    segs                         # y1, y2 rows
  )
  rownames(radar_df) <- c("max", "min", paste0(y1), paste0(y2))
  as.data.frame(radar_df)
}

# -----------------------------
# 5) Plot helper (unchanged)
# -----------------------------
plot_afford_radar <- function(profile_name, y1 = yrs_compare[1], y2 = yrs_compare[2],
                              col_y1 = alpha("#2C7BB6", 0.35), border_y1 = "#2C7BB6",
                              col_y2 = alpha("#D7191C", 0.35), border_y2 = "#D7191C") {
  radar_df <- make_radar_frame(afford, profile_name, y1, y2)
  if (is.null(radar_df)) { message("Skipping ", profile_name, " (missing one of the years)."); return(invisible(NULL)) }
  
  op <- par(mar = c(1.5, 2, 3.5, 2)); on.exit(par(op), add = TRUE)
  fmsb::radarchart(
    radar_df,
    axistype = 1, seg = 5,
    pcol = c(border_y1, border_y2),
    pfcol = c(col_y1, col_y2),
    plwd = 2.5, plty = 1,
    cglcol = "grey70", cglty = 1, cglwd = 0.8,
    axislabcol = "grey30", vlcex = 0.85
  )
  legend("topright", legend = c(as.character(y1), as.character(y2)),
         bty = "n", cex = 0.9, pch = 15, pt.cex = 1.2,
         col = c(border_y1, border_y2), text.col = "grey10")
  title(main = sprintf("Months of income by car segment — %s", profile_name),
        cex.main = 1.0, col.main = "grey10", font.main = 2)
  mtext("Lower is better (fewer months of income required)", side = 1, line = -1, adj = 0, col = "grey35", cex = 0.78)
}

# -----------------------------
# 6) Draw (as before)
# -----------------------------
if (!use_regions) {
  picks <- profiles[profiles %in% c("Persons - Full-time - Total",
                                    "Males - Full-time - Total",
                                    "Females - Full-time - Total")]
  for (p in picks) { plot.new(); plot_afford_radar(p) }
} else {
  for (p in profiles) { plot.new(); plot_afford_radar(p) }
}