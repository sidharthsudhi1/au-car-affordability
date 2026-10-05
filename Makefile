PY := .venv/bin/python

.PHONY: setup fetch data tables notebook test lint all

setup:
	python3.12 -m venv .venv
	$(PY) -m pip install -e ".[dev]"

fetch:
	$(PY) -m carafford.build --fetch

data:
	$(PY) -m carafford.build

tables:
	$(PY) -m carafford.analysis

notebook:
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests

all: data tables notebook test
