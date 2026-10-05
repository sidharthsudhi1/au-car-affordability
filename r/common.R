# Shared paths, theme and the Affordability Index (AI) build used by every R figure.
suppressPackageStartupMessages({
  library(tidyverse)
  library(scales)
})

root <- if (file.exists("pyproject.toml")) "." else ".."
clean <- file.path(root, "data", "clean")
out_dir <- file.path(root, "figures", "r")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

segments <- c("Hatchback", "Sedan", "SUV", "Ute", "Wagon")
seg_colours <- c(Hatchback = "#2a78d6", Sedan = "#eb6834", SUV = "#1baf7a", Ute = "#eda100", Wagon = "#e87ba4")
ink <- "#0b0b0b"
ink_2 <- "#52514e"
muted <- "#8a8984"
surface <- "#fcfcfb"

theme_report <- function(base_size = 12) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.background = element_rect(fill = surface, colour = NA),
      plot.title = element_text(face = "bold", size = rel(1.25), colour = ink),
      plot.title.position = "plot",
      plot.subtitle = element_text(colour = ink_2, margin = margin(b = 10)),
      plot.caption = element_text(colour = muted, size = rel(0.75), hjust = 0),
      plot.caption.position = "plot",
      axis.title = element_text(colour = ink_2),
      axis.text = element_text(colour = ink_2),
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = "#e6e5e1", linewidth = 0.4),
      legend.position = "top",
      legend.justification = "left",
      legend.title = element_blank(),
      plot.margin = margin(14, 18, 10, 14)
    )
}

save_fig <- function(plot, name, width = 8, height = 4.6) {
  ggsave(file.path(out_dir, paste0(name, ".png")), plot, width = width, height = height, dpi = 200, bg = surface)
}

# AI = annual median earnings / price of the median new car in a segment.
# Segment prices are the 2023 median new listing, moved through time with the ABS motor vehicles index.
segment_prices <- function() {
  seg <- read_csv(file.path(clean, "analysis", "new_segment_prices.csv"), show_col_types = FALSE)
  idx <- read_csv(file.path(clean, "analysis", "car_price_series.csv"), show_col_types = FALSE) |>
    transmute(year, rel = motor_vehicles_index / motor_vehicles_index[year == 2023])
  crossing(seg |> select(segment, price_2023 = median_price), idx) |>
    transmute(year, segment, price = price_2023 * rel)
}

earnings <- function() {
  read_csv(file.path(clean, "median_weekly_earnings.csv"), show_col_types = FALSE) |>
    filter(leave == "Total") |>
    mutate(annual = median_weekly * 52)
}

affordability <- function(state_filter = "AUS") {
  earnings() |>
    filter(state %in% state_filter) |>
    inner_join(segment_prices(), by = "year", relationship = "many-to-many") |>
    mutate(ai = annual / price)
}
