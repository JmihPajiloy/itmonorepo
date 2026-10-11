PYTHON ?= python3
TYPST ?= typst
EXTRACT_PYTHON ?= .venv/bin/python

.PHONY: check report screenshots

check:
	$(PYTHON) scripts/verify.py

report: check
	$(TYPST) compile --root ../../.. report.typ report.pdf

screenshots:
	$(EXTRACT_PYTHON) scripts/extract_screenshots.py
