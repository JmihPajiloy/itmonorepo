TYPST ?= typst
PY := .venv/bin/python

.PHONY: help venv check shots run report

help:
	@printf '%s\n' \
	  'make venv   - create .venv and install requirements' \
	  'make check  - rebuild DB, test app, save verification' \
	  'make shots  - screenshots of the running app (Chrome)' \
	  'make run    - start app on http://127.0.0.1:5000' \
	  'make report - build report.pdf'

venv:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements.txt

check:
	./check.sh

shots:
	$(PY) shots.py shots

run:
	$(PY) -m webapp

report:
	$(TYPST) compile --root ../../.. report.typ report.pdf
