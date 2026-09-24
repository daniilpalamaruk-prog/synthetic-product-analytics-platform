.PHONY: env setup install test lint generate-small quality warehouse acceptance airflow-up greenplum-up bi-up full-up down benchmark clean

VENV ?= .venv
ifeq ($(OS),Windows_NT)
BASE_PYTHON ?= python
VENV_PYTHON := $(VENV)/Scripts/python.exe
else
BASE_PYTHON ?= python3
VENV_PYTHON := $(VENV)/bin/python
endif

env:
	$(BASE_PYTHON) scripts/bootstrap_env.py

setup:
	$(BASE_PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip install -e .

install:
	$(BASE_PYTHON) -m pip install -r requirements.txt
	$(BASE_PYTHON) -m pip install -e .

test:
	$(VENV_PYTHON) -m pytest -q

lint:
	$(VENV_PYTHON) -m ruff check src tests analysis validation airflow/dags scripts

generate-small:
	$(VENV_PYTHON) generate.py --profile small --seed 42 --output data/small --csv-sample false

sample:
	$(VENV_PYTHON) generate.py --users 1000 --target-events 30000 --seed 42 --output sample/generated --csv-sample true

quality:
	$(VENV_PYTHON) quality.py --input data/small --layer raw
	$(VENV_PYTHON) quality.py --input data/small --layer clean

warehouse:
	$(VENV_PYTHON) warehouse.py --input data/small --database data/warehouse.db

acceptance: test
	$(VENV_PYTHON) generate.py --users 300 --target-events 6000 --seed 42 --output data/acceptance --csv-sample false
	$(VENV_PYTHON) quality.py --input data/acceptance --layer clean
	$(VENV_PYTHON) warehouse.py --input data/acceptance --database data/acceptance.db
	$(VENV_PYTHON) analysis/experiment_analysis.py --input data/acceptance --output data/acceptance/experiment_report.json --bootstrap-iterations 100
	$(VENV_PYTHON) analysis/validate_patterns.py --input data/acceptance --output data/acceptance/pattern_report.json
	$(VENV_PYTHON) analysis/business_cases.py --input data/acceptance --output business_cases

airflow-up:
	docker compose --profile core up -d airflow-init airflow-webserver airflow-scheduler

greenplum-up:
	docker compose --profile greenplum up -d greenplum

bi-up:
	docker compose --profile bi up -d superset

full-up: env
	docker compose --profile full up -d

down:
	docker compose --profile core --profile greenplum --profile bi --profile full down

benchmark:
	$(VENV_PYTHON) benchmarks/generator_benchmark.py --result benchmarks/results/generator.json

clean:
	$(VENV_PYTHON) scripts/clean_generated.py

.PHONY: reports
reports:
	$(VENV_PYTHON) analysis/validate_patterns.py --input sample/generated --output sample/generated/pattern_report.json
	$(VENV_PYTHON) analysis/experiment_analysis.py --input sample/generated --output sample/generated/experiment_report.json
