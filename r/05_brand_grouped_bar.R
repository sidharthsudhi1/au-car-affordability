source(file.path(if (file.exists("r/common.R")) "r" else ".", "common.R"))

listings_path <- file.path(root, "data", "interim", "listings_clean.csv")
if (!file.exists(listings_path)) stop("Run `make data` with the Kaggle file first")

cars <- read_csv(listings_path, show_col_types = FALSE) |>
  mutate(stage = case_when(
    condition %in% c("New", "Demo") ~ "New / demo",
    between(age, 4, 6) ~ "4-6 years old",
    between(age, 9, 11) ~ "9-11 years old"
  )) |>
  filter(!is.na(stage))

# Brands with enough listings at every stage for a stable median
brands <- cars |>
  count(brand, stage) |>
  group_by(brand) |>
  filter(n_distinct(stage) == 3, min(n) >= 25) |>
  summarise(total = sum(n)) |>
  slice_max(total, n = 10) |>
  pull(brand)

by_brand <- cars |>
  filter(brand %in% brands) |>
  group_by(brand, stage) |>
  summarise(median_price = median(price), n = n(), .groups = "drop") |>
  mutate(stage = factor(stage, levels = c("New / demo", "4-6 years old", "9-11 years old")),
         brand = fct_reorder(brand, median_price, .fun = max, .desc = TRUE))

p <- ggplot(by_brand, aes(brand, median_price, fill = stage)) +
  geom_col(position = position_dodge(width = 0.82), width = 0.78) +
  scale_fill_manual(values = c("New / demo" = "#2a78d6", "4-6 years old" = "#86b6ef", "9-11 years old" = "#cde2fb")) +
  scale_y_continuous(labels = dollar_format(scale = 1e-3, suffix = "k"), expand = expansion(mult = c(0, 0.05))) +
  labs(
    title = "Median listed price by brand: new, mid-life and ageing cars",
    subtitle = "2023 listings, raw medians. Model mix differs by age, so the like-for-like view is the hedonic model",
    x = NULL, y = NULL,
    caption = "Source: Kaggle Australian Vehicle Prices (2023 snapshot). Brands with 25+ listings at every stage"
  ) +
  theme_report() +
  theme(panel.grid.major.x = element_blank(), axis.text.x = element_text(colour = ink))

save_fig(p, "05_brand_grouped_bar", height = 4.6)
