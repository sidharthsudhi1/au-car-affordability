PY := .venv/bin/python

.PHONY: setup fetch data tables figures r notebook test lint all

setup:
	python3.12 -m venv .venv
	$(PY) -m pip install -e ".[dev]"

fetch:
	$(PY) -m carafford.build --fetch

data:
	$(PY) -m carafford.build

tables:
	$(PY) -m carafford.analysis

figures:
	$(PY) -m carafford.figures

r:
	Rscript r/run_all.R

notebook:
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests scraping

all: data tables figures r notebook test
