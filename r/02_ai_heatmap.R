source(file.path(if (file.exists("r/common.R")) "r" else ".", "common.R"))

# Typical car = median 2023 new listing across all segments, so groups are compared on one price
typical <- read_csv(file.path(clean, "analysis", "car_price_series.csv"), show_col_types = FALSE) |>
  select(year, car_price)

groups <- earnings() |>
  filter(state == "AUS", sex != "Persons", work_status != "Total") |>
  inner_join(typical, by = "year") |>
  mutate(group = paste(work_status, str_to_lower(sex)), ai = annual / car_price) |>
  group_by(group) |>
  mutate(ai_rebased = ai / ai[year == 2014]) |>
  ungroup() |>
  mutate(group = fct_reorder(group, ai))

p <- ggplot(groups, aes(factor(year), group, fill = ai_rebased)) +
  geom_tile(colour = surface, linewidth = 1.2) +
  geom_text(aes(label = number(ai, accuracy = 0.01), colour = ai_rebased > 1.25), size = 3.2) +
  scale_fill_gradient(low = "#e8f1fc", high = "#184f95", labels = label_number(accuracy = 0.1),
                      name = "AI vs 2014") +
  scale_colour_manual(values = c(`TRUE` = "white", `FALSE` = ink), guide = "none") +
  labs(
    title = "Affordability improved for every group; part-time workers stay far behind",
    subtitle = "AI = annual median earnings / typical new car price. Text: AI. Shade: AI relative to 2014.\nAug 2020 was surveyed during COVID-19 lockdowns",
    x = NULL, y = NULL,
    caption = "Source: ABS Employee Earnings (Aug), ABS CPI motor vehicles; typical car anchored to the 2023 median new listing"
  ) +
  theme_report() +
  theme(panel.grid = element_blank(), legend.position = "right", legend.title = element_text(colour = ink_2, size = 9))

save_fig(p, "02_ai_heatmap", height = 3.6)
