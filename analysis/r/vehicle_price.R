# ============================================================
# Horizon-style small multiples (no ggHoriPlot)
# Growth vs 2014 baseline, by segment (2014–last available year)
# ============================================================

library(tidyverse)
library(scales)
library(readr)

# ---------- 1) Load & scope ----------
veh <- read_csv("vehicle_prices_clean.csv", show_col_types = FALSE)

veh_seg <- veh %>%
  filter(!is.na(price), !is.na(bodytype_std)) %>%
  filter(year >= 2014, year <= 2024)

min_year <- min(veh_seg$year, na.rm = TRUE)
max_year <- max(veh_seg$year, na.rm = TRUE)

# ---------- 2) Segment medians & 2014 baseline ----------
seg_med <- veh_seg %>%
  group_by(bodytype_std, year) %>%
  summarise(med = median(price, na.rm = TRUE), n = n(), .groups = "drop")

baseline_2014 <- seg_med %>%
  filter(year == 2014) %>%
  select(bodytype_std, med_2014 = med)

# Keep only segments that actually have a 2014 baseline
seg_med <- seg_med %>%
  inner_join(baseline_2014, by = "bodytype_std") %>%
  mutate(
    seg     = bodytype_std,
    dev     = (med / med_2014) - 1  # deviation vs 2014 (e.g., 0.25 = +25%)
  )

# Keep well-represented segments, and order by last-year growth
keep_segments <- seg_med %>%
  group_by(seg) %>%
  summarise(years = n_distinct(year), total_n = sum(n), .groups = "drop") %>%
  filter(years >= 8, total_n >= 150) %>%
  pull(seg)

seg_med <- seg_med %>% filter(seg %in% keep_segments)

last_year <- max(seg_med$year, na.rm = TRUE)
seg_order <- seg_med %>%
  filter(year == last_year) %>%
  arrange(desc(dev)) %>%
  pull(seg)

seg_med <- seg_med %>%
  mutate(seg = factor(seg, levels = seg_order))

# ---------- 3) Build horizon bands manually ----------
# Choose band height in % (e.g., 0.10 = 10% per band)
band <- 0.10

# Helper to compute one positive band (k = 0,1,2,...) for a vector v
band_pos <- function(v, k, band) pmax(pmin(v - k*band, band), 0)
# Helper for negative bands (mirror)
band_neg <- function(v, k, band) -pmax(pmin(-v - k*band, band), 0)

# For each segment×year dev value, expand into multiple band layers
make_bands <- function(df, band = 0.10) {
  # how many bands needed overall (symmetrically)
  max_pos <- ceiling(max(df$dev, na.rm = TRUE) / band)
  max_neg <- ceiling(-min(df$dev, na.rm = TRUE) / band)
  pos_idx <- if (max_pos > 0) 0:(max_pos-1) else integer(0)
  neg_idx <- if (max_neg > 0) 0:(max_neg-1) else integer(0)
  
  # positive bands
  pos_layers <- map_df(pos_idx, function(k) {
    tibble(
      year   = df$year,
      seg    = df$seg,
      layer  = paste0("pos_", k),
      level  = k + 1L,                 # 1..N (used for fill intensity)
      value  = band_pos(df$dev, k, band)   # height of that band at each year
    ) %>% filter(value > 0)
  })
  
  # negative bands
  neg_layers <- map_df(neg_idx, function(k) {
    tibble(
      year   = df$year,
      seg    = df$seg,
      layer  = paste0("neg_", k),
      level  = k + 1L,
      value  = band_neg(df$dev, k, band)
    ) %>% filter(value < 0)
  })
  
  bind_rows(pos_layers, neg_layers)
}

bands_long <- seg_med %>%
  arrange(seg, year) %>%
  group_by(seg) %>%
  group_modify(~ make_bands(.x, band = band)) %>%
  ungroup()

# ---------- 4) Plot horizon-style small multiples ----------
# We draw banded areas centered at 0 in each facet; higher |level| -> stronger color.
# Use a diverging palette: reds for positive, blues for negative.
pal_pos <- colorRampPalette(c("#FECACA", "#F87171", "#B91C1C")) # light->strong red
pal_neg <- colorRampPalette(c("#BFDBFE", "#60A5FA", "#1D4ED8")) # light->strong blue

# Map levels to colors separately for pos/neg:
bands_long <- bands_long %>%
  mutate(
    sign = ifelse(value >= 0, "pos", "neg"),
    # scale 'level' per sign so deepest band gets strongest color
    level_scaled = level
  )

# Determine max levels per sign to build palettes of right length
max_level_pos <- bands_long %>% filter(sign == "pos") %>% summarise(m = max(level, na.rm = TRUE)) %>% pull(m)
max_level_neg <- bands_long %>% filter(sign == "neg") %>% summarise(m = max(level, na.rm = TRUE)) %>% pull(m)

cols_pos <- if (is.finite(max_level_pos) && max_level_pos > 0) pal_pos(max_level_pos) else character(0)
cols_neg <- if (is.finite(max_level_neg) && max_level_neg > 0) pal_neg(max_level_neg) else character(0)
cols_map <- c(setNames(cols_neg, paste0("neg_", 1:max_level_neg)),
              setNames(cols_pos, paste0("pos_", 1:max_level_pos)))

# Build the plot
p_horizon_custom <- ggplot(bands_long, aes(x = year, y = value, group = layer)) +
  geom_area(aes(fill = paste0(sign, "_", level)), position = "identity", linewidth = 0) +
  geom_hline(yintercept = 0, colour = "grey70", linewidth = 0.2) +
  scale_fill_manual(values = cols_map, guide = "none") +
  facet_grid(rows = vars(seg), switch = "y") +
  scale_x_continuous(breaks = seq(min_year, max_year, by = 1)) +
  # Compress each facet to one band-height up/down (classic horizon collapse)
  coord_cartesian(ylim = c(-band, band), expand = FALSE) +
  labs(
    title = "Horizon-style bands: growth in segment medians relative to 2014",
    subtitle = paste0(
      "Each row = one segment. Baseline is 2014 (0). Bands are ±", percent(band),
      " increments; deeper color = larger deviation."
    ),
    x = "Year", y = NULL,
    caption = "Source: Redbook scrape (cleaned), 2014–2024."
  ) +
  theme_minimal(base_size = 12) +
  theme(
    strip.text.y.left = element_text(angle = 0, hjust = 1, face = "bold"),
    panel.grid = element_blank(),
    axis.text.y  = element_blank(),
    axis.ticks.y = element_blank(),
    plot.title   = element_text(face = "bold"),
    axis.title.x = element_text(face = "bold")
  )

p_horizon_custom

# Optional save
# dir.create("figs", showWarnings = FALSE)
# ggsave("figs/horizon_segments_custom.png", p_horizon_custom,
#        width = 12, height = 9, dpi = 300, bg = "white")
