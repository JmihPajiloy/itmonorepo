PYTHON ?= python3
TYPST ?= typst

.PHONY: help check report

help:
	@printf '%s\n' 'make check  - verify SQL and regenerate demo data' 'make report - regenerate ER diagram and PDF'

check:
	$(PYTHON) verify.py

report:
	$(PYTHON) diagrams/generate.py
	$(TYPST) compile --root ../../.. report.typ report.pdf
