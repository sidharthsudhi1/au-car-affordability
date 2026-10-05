# Australian state boundaries for the dashboard choropleth, from Natural Earth (public domain).
suppressPackageStartupMessages(library(sf))
url <- "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
zip <- tempfile(fileext = ".zip")
download.file(url, zip, quiet = TRUE, mode = "wb")
dir <- tempfile()
unzip(zip, exdir = dir)
shp <- list.files(dir, pattern = "\\.shp$", full.names = TRUE)
abbrev <- c("New South Wales" = "NSW", "Victoria" = "VIC", "Queensland" = "QLD", "Western Australia" = "WA",
            "South Australia" = "SA", "Tasmania" = "TAS", "Northern Territory" = "NT",
            "Australian Capital Territory" = "ACT")
states <- st_read(shp, quiet = TRUE)
states <- states[states$adm0_a3 == "AUS" & states$name %in% names(abbrev), "name"]
states$state <- unname(abbrev[states$name])
states <- st_simplify(st_transform(states, 3577), dTolerance = 4000, preserveTopology = TRUE)
states <- st_transform(states, 4326)
out <- file.path(if (file.exists("pyproject.toml")) "." else "..", "dashboard", "aus_states.geojson")
if (file.exists(out)) file.remove(out)
st_write(states[, c("state", "name")], out, quiet = TRUE, layer_options = "COORDINATE_PRECISION=3")
cat(nrow(states), "states,", round(file.size(out) / 1024), "KB\n")
