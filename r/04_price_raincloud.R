source(file.path(if (file.exists("r/common.R")) "r" else ".", "common.R"))
suppressPackageStartupMessages(library(ggdist))

listings_path <- file.path(root, "data", "interim", "listings_clean.csv")
if (!file.exists(listings_path)) stop("Run `make data` with the Kaggle file first")

new_cars <- read_csv(listings_path, show_col_types = FALSE) |>
  filter(condition %in% c("New", "Demo"), body_type %in% segments) |>
  mutate(segment = fct_reorder(body_type, price, .fun = median))

meds <- new_cars |> group_by(segment) |> summarise(med = median(price), n = n())

p <- ggplot(new_cars, aes(price, segment, fill = segment, colour = segment)) +
  stat_halfeye(adjust = 0.6, height = 0.6, justification = -0.25, .width = 0, point_colour = NA, alpha = 0.55) +
  geom_boxplot(width = 0.14, outlier.shape = NA, alpha = 0.3, linewidth = 0.4) +
  geom_point(position = position_jitter(height = 0.06, seed = 5147), size = 0.5, alpha = 0.25, shape = 16) +
  geom_text(data = meds, aes(x = med, y = segment, label = paste0(dollar(med, scale = 1e-3, suffix = "k", accuracy = 1), "  n=", n)),
            inherit.aes = FALSE, nudge_y = 0.42, size = 3.1, colour = ink, hjust = 0) +
  scale_x_log10(labels = dollar_format(scale = 1e-3, suffix = "k", accuracy = 1), breaks = c(20e3, 30e3, 50e3, 80e3, 120e3, 200e3)) +
  scale_fill_manual(values = seg_colours, guide = "none") +
  scale_colour_manual(values = seg_colours, guide = "none") +
  labs(
    title = "Hatchbacks are the only segment with a new-car median under $35k",
    subtitle = "New and demo listings, 2023. Cloud = distribution, box = interquartile range, dots = listings",
    x = "listed price (log scale)", y = NULL,
    caption = "Source: Kaggle Australian Vehicle Prices (2023 snapshot)"
  ) +
  theme_report() +
  theme(panel.grid.major.y = element_blank())

save_fig(p, "04_price_raincloud", height = 5)
