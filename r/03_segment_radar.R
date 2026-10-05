source(file.path(if (file.exists("r/common.R")) "r" else ".", "common.R"))
suppressPackageStartupMessages(library(fmsb))

ai <- affordability() |>
  filter(year == 2024, sex != "Persons", work_status != "Total") |>
  mutate(group = paste(work_status, str_to_lower(sex))) |>
  select(group, segment, ai) |>
  pivot_wider(names_from = segment, values_from = ai) |>
  column_to_rownames("group")
ai <- ai[c("Full-time males", "Full-time females", "Part-time females", "Part-time males"), segments]

group_colours <- c("#2a78d6", "#1baf7a", "#eb6834", "#eda100")
limit <- ceiling(max(ai) * 4) / 4
radar_data <- rbind(rep(limit, ncol(ai)), rep(0, ncol(ai)), ai)

png(file.path(out_dir, "03_segment_radar.png"), width = 8, height = 6.4, units = "in", res = 200, bg = surface)
par(mar = c(1, 1, 4.5, 1), family = "sans")
radarchart(
  radar_data, axistype = 1, seg = 4,
  pcol = group_colours, pfcol = adjustcolor(group_colours, alpha.f = 0.12), plwd = 2.2, plty = 1,
  cglcol = "#d6d5d0", cglty = 1, cglwd = 0.8, axislabcol = ink_2,
  caxislabels = number(seq(0, limit, length.out = 5), accuracy = 0.01),
  vlcex = 1, calcex = 0.75, vlabels = segments
)
title(main = "How many new cars a year's pay buys, by segment (2024)", adj = 0, cex.main = 1.25, line = 2.6)
mtext("Affordability Index = annual median earnings / median new price in the segment. Further out = more affordable",
      side = 3, adj = 0, line = 1.2, cex = 0.8, col = ink_2)
legend("bottomright", legend = rownames(ai), col = group_colours, lwd = 2.2, bty = "n", cex = 0.85, text.col = ink)
mtext("Source: ABS Employee Earnings Aug 2024; Kaggle Australian Vehicle Prices (2023) moved with ABS CPI",
      side = 1, adj = 0, line = -0.2, cex = 0.65, col = muted)
invisible(dev.off())
