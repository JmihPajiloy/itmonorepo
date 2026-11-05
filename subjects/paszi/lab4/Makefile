PYTHON ?= python3
TYPST ?= typst

.PHONY: env up down start stop check report shots archive materials

start:
	./start.sh

stop:
	./start.sh --stop

env:
	$(PYTHON) scripts/init_env.py

up: env
	docker compose up --build -d --wait

down:
	docker compose down

check: env
	mkdir -p verification
	docker compose --profile test run --build --rm tests

shots:
	cd frontend && npm run shots

materials:
	$(PYTHON) scripts/verify_materials.py

report: materials
	$(TYPST) compile --root ../../.. report.typ report.pdf

archive:
	$(PYTHON) scripts/archive.py
