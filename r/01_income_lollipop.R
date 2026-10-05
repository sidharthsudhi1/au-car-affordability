source(file.path(if (file.exists("r/common.R")) "r" else ".", "common.R"))

income <- earnings() |>
  filter(state == "AUS", sex == "Persons", work_status == "Total") |>
  arrange(year)

growth <- last(income$annual) / first(income$annual) - 1

p <- ggplot(income, aes(year, annual)) +
  geom_segment(aes(xend = year, y = 0, yend = annual), linewidth = 0.8, colour = "#c9c8c2", lineend = "round") +
  geom_point(size = 4, colour = seg_colours[["Hatchback"]]) +
  geom_text(aes(label = dollar(annual, accuracy = 1, scale = 1e-3, suffix = "k")),
            vjust = -1.3, size = 3.4, colour = ink, fontface = "bold") +
  scale_x_continuous(breaks = income$year) +
  scale_y_continuous(labels = dollar_format(scale = 1e-3, suffix = "k"), limits = c(0, max(income$annual) * 1.12),
                     expand = expansion(mult = c(0, 0.02))) +
  labs(
    title = sprintf("Median annual earnings rose %s between 2014 and 2024", percent(growth)),
    subtitle = "All employees, Australia. Median weekly earnings in August x 52",
    x = NULL, y = NULL,
    caption = "Source: ABS Employee Earnings, August 2014-2024"
  ) +
  theme_report() +
  theme(panel.grid.major.x = element_blank())

save_fig(p, "01_income_lollipop")
