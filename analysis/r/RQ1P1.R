# ============================================================
# Bar chart: Average new-car prices by brand, grouped in 3-year intervals
# ============================================================

library(tidyverse)
library(scales)
library(readr)
library(forcats)

# 1) Load & scope
veh <- read_csv("vehicle_prices_clean.csv", show_col_types = FALSE) %>%
  filter(between(year, 2014, 2024), !is.na(price), !is.na(brand))

# Gentle outlier clamp (1–99%)
b <- quantile(veh$price, c(0.01, 0.99), na.rm = TRUE)
veh <- veh %>% mutate(price_clip = pmin(pmax(price, b[1]), b[2]))

# 2) Define year groups (3-year bins)
veh <- veh %>%
  mutate(year_group = case_when(
    year %in% 2014:2016 ~ "2014–2016",
    year %in% 2017:2019 ~ "2017–2019",
    year %in% 2020:2023 ~ "2020–2023",
    TRUE ~ NA_character_
  ))

# 3) Compute mean per brand × year_group
brand_group <- veh %>%
  filter(!is.na(year_group)) %>%
  group_by(brand, year_group) %>%
  summarise(
    n = n(),
    mean_price = mean(price_clip, na.rm = TRUE),
    .groups = "drop"
  )

library(forcats)

# Top brands by volume in latest group (unchanged)
top_brands <- brand_group %>%
  filter(year_group == "2020–2023") %>%
  arrange(desc(n)) %>%
  slice_head(n = 15) %>%
  pull(brand)

# 1) Compute one value per brand for ordering (latest-group mean)
latest_means <- brand_group %>%
  filter(year_group == "2020–2023", brand %in% top_brands) %>%
  group_by(brand) %>%
  summarise(latest_mean = mean(mean_price, na.rm = TRUE), .groups = "drop")

# 2) Join and reorder safely
plot_df <- brand_group %>%
  filter(brand %in% top_brands) %>%
  left_join(latest_means, by = "brand") %>%
  mutate(
    brand = fct_reorder(brand, latest_mean, .desc = TRUE),
    year_group = factor(year_group, levels = c("2014–2016", "2017–2019", "2020–2023"))
  )

p_grouped <- ggplot(plot_df, aes(x = brand, y = mean_price, fill = year_group)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.68) +
  geom_text(aes(label = scales::dollar(mean_price, prefix = "$", big.mark = ",")),
            position = position_dodge(width = 0.72), vjust = -0.25, size = 3) +
  
  # --- Y axis: start at 0, increments of 20k ---
  scale_y_continuous(
    limits = c(0, ceiling(max(plot_df$mean_price, na.rm = TRUE) * 1.1 / 20000) * 20000),
    breaks = seq(0, ceiling(max(plot_df$mean_price, na.rm = TRUE) * 1.1 / 20000) * 20000, by = 20000),
    labels = scales::label_dollar(prefix = "$", big.mark = ",")
  ) +
  
  scale_fill_manual(values = c("2014–2016"="#4E79A7", "2017–2019"="#E15759", "2020–2023"="#76B7B2"),
                    name = "Year Group") +
  labs(
    title = "Average new-car prices by brand (3-year group comparison)",
    subtitle = "Top brands by volume in 2020–2023. Means after 1–99% outlier clamping.",
    x = "Brand", y = "Average price (AUD)",
    caption = "Source: Redbook scrape (cleaned), 2014–2024"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title   = element_text(face = "bold"),
    plot.subtitle= element_text(colour = "grey30"),
    panel.grid.minor = element_blank(),
    
    # --- Bold black axis titles and labels ---
    axis.title.x = element_text(face = "bold", colour = "black", margin = margin(t = 6)),
    axis.title.y = element_text(face = "bold", colour = "black", margin = margin(r = 6)),
    axis.text.x  = element_text(face = "bold", colour = "black"),
    axis.text.y  = element_text(face = "bold", colour = "black")
  )

p_grouped
