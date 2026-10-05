library(tidyverse)
library(scales)
library(readr)

# ---- data ----
abs_income <- read_csv("abs_income_national_yearly.csv", show_col_types = FALSE) |>
  filter(between(year, 2014, 2024)) |>
  arrange(year)

library(ggplot2)
library(scales)

# Assuming your dataset is called abs_income
# abs_income has columns: year, annual_median_aud

# Y-axis breaks
ymax <- max(abs_income$annual_median_aud, na.rm = TRUE)
ybrks <- seq(0, ymax * 1.1, by = 10000)

# ---- Clean Lollipop Plot ----
p <- ggplot(abs_income, aes(x = year, y = annual_median_aud)) +
  # stick (vertical line from 0 to dot)
  geom_segment(aes(xend = year, y = 0, yend = annual_median_aud),
               linewidth = 0.7, colour = "grey55", lineend = "round") +
  # dot
  geom_point(size = 3.8, colour = "#1B76D1") +
  # labels above dots
  geom_text(aes(label = dollar(annual_median_aud, prefix = "$", big.mark = ",")),
            vjust = -1.0, size = 3.8, fontface = "bold") +
  # axes scaling
  scale_x_continuous(breaks = abs_income$year) +
  scale_y_continuous(
    breaks = ybrks,
    labels = dollar_format(prefix = "$", big.mark = ","),
    limits = c(0, ymax * 1.10),
    expand = expansion(mult = c(0, 0.08))
  ) +
  # labels
  labs(
    title = "Annual Median Income in Australia (2014–2024)",
    subtitle = "Dot marks annual median income; sticks show scale from baseline",
    x = "Year",
    y = "Annual Median Income (AUD)",
    caption = "Source: ABS Median Weekly Earnings (cleaned)."
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title   = element_text(face = "bold", size = 16),
    plot.subtitle= element_text(colour = "grey35"),
    axis.title.x = element_text(face = "bold", size = 13),
    axis.title.y = element_text(face = "bold", size = 13),
    axis.text.x  = element_text(face = "bold", size = 12, margin = margin(t = 6)),
    axis.text.y  = element_text(face = "bold", size = 12, margin = margin(r = 6)),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_blank(),
    panel.grid.major.y = element_line(colour = "grey88"),
    plot.caption = element_text(colour = "grey40", size = 10)
  )

p