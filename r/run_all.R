here <- if (file.exists("r/run_all.R")) "r" else "."
for (f in sort(list.files(here, pattern = "^[0-9]{2}_.*\\.R$", full.names = TRUE))) {
  message("running ", basename(f))
  source(f, local = new.env())
}
